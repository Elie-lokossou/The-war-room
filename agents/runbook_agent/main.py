import uuid
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()


def analyze(task: TriageTask, severity: Severity) -> Finding:
    keywords = ["runbook", "mitigation", "playbook", "remediation", "rollback", "restart", "failover"]
    matched_keywords = [keyword for keyword in keywords if keyword in task.description.lower()]

    if severity > Severity.MEDIUM and matched_keywords:
        finding_type = "runbook_match"
        confidence = 0.75
        value = ", ".join(matched_keywords)
        hypothesis = f"Runbook match found for incident {task.incident_id} with keywords: {value}"
        recommended_action = "Runbook suggests: investigate and mitigate"
    else:
        finding_type = "runbook_note"
        confidence = 0.55
        value = "no_runbook_match"
        hypothesis = f"No specific runbook match found for incident {task.incident_id}"
        recommended_action = "No action needed"

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="runbook-agent",
        finding_type=finding_type,
        signal="runbook_analysis",
        value=value,
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Runbook analysis for {task.incident_id}: {finding_type}",
        supporting_data={"recommended_action": recommended_action}
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
    band.publish("triage-findings", result.model_dump(), "runbook-agent")
    if severity <= Severity.MEDIUM:
        band.publish(
            "deliberation",
            {
                "sender": "runbook-agent",
                "content": (
                    f"Low severity triage complete for {task.incident_id}. "
                    "No runbook match found."
                ),
            },
            "runbook-agent",
        )


def start():
    band.subscribe("triage-tasks", handle_task)
    while True:
        band.poll("triage-tasks")
