import uuid
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()


def analyze(task, severity: Severity) -> Finding:
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
