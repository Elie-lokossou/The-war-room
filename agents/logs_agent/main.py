import uuid
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()

def analyze(task: TriageTask, severity: Severity) -> Finding:
    error_patterns = ["error", "exception", "trace", "timeout", "stack", "5xx", "crash"]
    found_patterns = [
        pattern for pattern in error_patterns if pattern in task.description.lower()
    ]

    if severity > Severity.MEDIUM:
        finding_type = "log_anomaly"
        confidence = 0.85
        hypothesis = f"High severity incident ({severity.name}) with significant log error patterns detected: {', '.join(found_patterns) or 'no_errors'}."
    else:
        finding_type = "log_observation"
        confidence = 0.65
        hypothesis = f"Low severity incident ({severity.name}), log analysis shows {', '.join(found_patterns) or 'no_errors'} patterns."

    value = ", ".join(found_patterns) or "no_errors"

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="logs-agent",
        finding_type=finding_type,
        signal="log_pattern_analysis",
        value=value,
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Log analysis for incident {task.incident_id}: {finding_type}",
    )


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
