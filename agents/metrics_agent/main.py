import json
import uuid
import pathlib
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()


def _analyze_from_file(task: TriageTask) -> Finding:
    data_file = pathlib.Path(task.data_path) / "metrics" / "snapshots.json"
    data = json.loads(data_file.read_text())
    snapshots = data.get("snapshots", [])
    if not snapshots:
        return None

    baseline_p99 = snapshots[0].get("baseline_p99_ms", 120)
    peak_p99_snap = max(snapshots, key=lambda s: s.get("p99_latency_ms", 0))
    peak_err_snap = max(snapshots, key=lambda s: s.get("error_rate_pct", 0.0))
    peak_pool_snap = max(snapshots, key=lambda s: s.get("connection_pool_usage_pct", 0))

    p99 = peak_p99_snap.get("p99_latency_ms", baseline_p99)
    error_rate = peak_err_snap.get("error_rate_pct", 0.0)
    pool_pct = peak_pool_snap.get("connection_pool_usage_pct", 0)
    cpu_pct = peak_p99_snap.get("cpu_pct", 0)
    peak = peak_p99_snap if p99 > 0 else peak_err_snap

    latency_ratio = p99 / baseline_p99 if baseline_p99 else 1.0
    is_pool_exhausted = pool_pct >= 90
    is_latency_anomaly = latency_ratio >= 3.0
    is_error_spike = error_rate >= 2.0
    is_cpu_critical = cpu_pct >= 95
    is_total_outage = error_rate >= 80.0

    if is_total_outage or is_cpu_critical:
        finding_type = "anomaly"
        confidence = 0.95
        signal = "total_outage" if is_total_outage else "cpu_saturation"
        hypothesis = f"Full service degradation detected: error_rate={error_rate}%, cpu={cpu_pct}%"
    elif is_pool_exhausted and is_latency_anomaly:
        finding_type = "anomaly"
        confidence = 0.92
        signal = "connection_pool_exhaustion"
        hypothesis = f"Connection pool exhaustion driving latency spike: pool={pool_pct}%, p99={p99}ms vs baseline {baseline_p99}ms"
    elif is_latency_anomaly or is_error_spike:
        finding_type = "anomaly"
        confidence = 0.85
        signal = "latency_spike"
        hypothesis = f"Latency anomaly detected: p99={p99}ms vs baseline {baseline_p99}ms (×{latency_ratio:.1f}), error_rate={error_rate}%"
    else:
        finding_type = "observation"
        confidence = 0.70
        signal = "elevated_latency"
        hypothesis = f"Mild latency elevation: p99={p99}ms vs baseline {baseline_p99}ms, likely transient"

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="metrics-agent",
        finding_type=finding_type,
        signal=signal,
        value=f"p99={p99}ms (baseline={baseline_p99}ms), pool={pool_pct}%, error_rate={error_rate}%, cpu={cpu_pct}%",
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Metrics analysis for {task.incident_id}: {finding_type} — {signal}",
        supporting_data={
            "peak_p99_ms": p99,
            "baseline_p99_ms": baseline_p99,
            "latency_ratio": round(latency_ratio, 2),
            "pool_pct": pool_pct,
            "error_rate_pct": error_rate,
            "cpu_pct": cpu_pct,
            "peak_timestamp": peak_p99_snap.get("timestamp", ""),
        },
    )


def _analyze_from_description(task: TriageTask, severity: Severity) -> Finding:
    finding_type = "anomaly" if severity > Severity.MEDIUM else "observation"
    confidence = 0.9 if finding_type == "anomaly" else 0.7
    hypothesis = (
        f"System severity is {severity.name}"
        if finding_type == "anomaly"
        else "No issues detected"
    )
    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="metrics-agent",
        finding_type=finding_type,
        signal="simulated_analysis",
        value=f"severity={severity.name}",
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Metrics analysis for {task.incident_id}: {finding_type}",
    )


def analyze(task: TriageTask, severity: Severity) -> Finding:
    if task.data_path:
        data_file = pathlib.Path(task.data_path) / "metrics" / "snapshots.json"
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

    if task.assigned_to != "@metrics-agent":
        return

    severity = _extract_severity(task)
    result = analyze(task, severity)
    band.publish("triage-findings", result.model_dump(), "metrics-agent")
    if severity <= Severity.MEDIUM:
        band.publish(
            "deliberation",
            {
                "sender": "metrics-agent",
                "content": (
                    f"Low severity triage complete for {task.incident_id}. "
                    "No anomalies detected."
                ),
            },
            "metrics-agent",
        )


def start():
    band.subscribe("triage-tasks", handle_task)
    while True:
        band.poll("triage-tasks")
