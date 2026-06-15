import json
import uuid
import pathlib
from collections import Counter
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()

_EXCEPTION_SIGNALS = {
    "ConnectionPoolExhaustedException": "connection_pool_exhaustion",
    "NullPointerException": "null_reference_crash",
    "OutOfMemoryError": "oom_crash",
    "TimeoutException": "timeout",
    "ProcessCrash": "process_crash",
}


def _analyze_from_file(task: TriageTask) -> Finding:
    data_file = pathlib.Path(task.data_path) / "logs" / "events.jsonl"
    lines = [json.loads(l) for l in data_file.read_text().splitlines() if l.strip()]

    error_lines = [l for l in lines if l.get("level") in ("ERROR", "FATAL")]
    warn_lines = [l for l in lines if l.get("level") == "WARN"]

    exception_counts: Counter = Counter()
    for entry in error_lines:
        exc = entry.get("exception")
        if exc:
            exception_counts[exc] += 1

    has_fatal = any(l.get("level") == "FATAL" for l in lines)
    total_errors = len(error_lines)
    dominant_exception = exception_counts.most_common(1)[0] if exception_counts else None

    if has_fatal and dominant_exception:
        exc_name, count = dominant_exception
        signal = _EXCEPTION_SIGNALS.get(exc_name, "unclassified_exception")
        finding_type = "log_anomaly"
        confidence = 0.92
        hypothesis = f"FATAL exceptions detected: {exc_name} × {count} — indicates service crash or unrecoverable error"
        value = f"{exc_name}×{count}, total_errors={total_errors}"
    elif dominant_exception:
        exc_name, count = dominant_exception
        signal = _EXCEPTION_SIGNALS.get(exc_name, "unclassified_exception")
        finding_type = "log_anomaly"
        confidence = 0.88
        hypothesis = f"Recurring exception: {exc_name} × {count} errors in incident window"
        value = f"{exc_name}×{count}, warn={len(warn_lines)}"
    elif total_errors > 0:
        signal = "elevated_errors"
        finding_type = "log_anomaly"
        confidence = 0.75
        hypothesis = f"{total_errors} errors in log window without a dominant exception pattern"
        value = f"errors={total_errors}, warnings={len(warn_lines)}"
    elif warn_lines:
        signal = "slow_queries"
        finding_type = "log_observation"
        confidence = 0.65
        hypothesis = f"{len(warn_lines)} warnings detected — likely slow queries or degraded performance"
        value = f"warnings={len(warn_lines)}, errors=0"
    else:
        signal = "no_errors"
        finding_type = "log_observation"
        confidence = 0.60
        hypothesis = "No errors or warnings found in log window — system appears healthy"
        value = "no_errors"

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="logs-agent",
        finding_type=finding_type,
        signal=signal,
        value=value,
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Log analysis for {task.incident_id}: {finding_type} — {signal}",
        supporting_data={
            "total_errors": total_errors,
            "total_warnings": len(warn_lines),
            "fatal_count": sum(1 for l in lines if l.get("level") == "FATAL"),
            "exception_counts": dict(exception_counts),
        },
    )


def _analyze_from_description(task: TriageTask, severity: Severity) -> Finding:
    error_patterns = ["error", "exception", "trace", "timeout", "stack", "5xx", "crash"]
    found_patterns = [p for p in error_patterns if p in task.description.lower()]

    if severity > Severity.MEDIUM:
        finding_type = "log_anomaly"
        confidence = 0.85
        hypothesis = f"High severity incident ({severity.name}) with log error patterns: {', '.join(found_patterns) or 'no_errors'}."
    else:
        finding_type = "log_observation"
        confidence = 0.65
        hypothesis = f"Low severity incident ({severity.name}), patterns: {', '.join(found_patterns) or 'no_errors'}."

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="logs-agent",
        finding_type=finding_type,
        signal="log_pattern_analysis",
        value=", ".join(found_patterns) or "no_errors",
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Log analysis for incident {task.incident_id}: {finding_type}",
    )


def analyze(task: TriageTask, severity: Severity) -> Finding:
    if task.data_path:
        data_file = pathlib.Path(task.data_path) / "logs" / "events.jsonl"
        if data_file.exists():
            result = _analyze_from_file(task)
            if result:
                return result
    return _analyze_from_description(task, severity)


def _extract_severity(task: TriageTask) -> Severity:
    if "CRITICAL" in task.description or "SEV-1" in task.description:
        return Severity.CRITICAL
    if "HIGH" in task.description or "spike" in task.description.lower():
        return Severity.HIGH
    if "MEDIUM" in task.description or "slow" in task.description.lower():
        return Severity.MEDIUM
    return Severity.LOW


def handle_task(envelope):
    payload = envelope["payload"]
    task = TriageTask(**payload)

    if task.assigned_to != "@logs-agent":
        return

    severity = _extract_severity(task)
    result = analyze(task, severity)
    band.publish("triage-findings", result.model_dump(), "logs-agent")
    if severity <= Severity.MEDIUM:
        band.publish(
            "deliberation",
            {
                "sender": "logs-agent",
                "content": (
                    f"Low severity log triage complete for {task.incident_id}. "
                    "No critical log anomalies detected."
                ),
            },
            "logs-agent",
        )


def start():
    band.subscribe("triage-tasks", handle_task)
    while True:
        band.poll("triage-tasks")
