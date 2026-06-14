import uuid
import logging
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

# Initialize BandClientWrapper at the module level
band = BandClientWrapper()

# Configure logging for the agent
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze(task: TriageTask, severity: Severity) -> Finding:
    """
    Analyzes a TriageTask for change correlation based on severity and task description.
    """
    keywords = ["deploy", "release", "config", "change", "rollback", "update", "migration"]
    task_description_lower = task.description.lower()
    correlated_changes = [kw for kw in keywords if kw in task_description_lower]

    if severity > Severity.MEDIUM and correlated_changes:
        finding_type = "change_correlation"
        confidence = 0.80
        value = ", ".join(correlated_changes)
        hypothesis = f"High severity incident correlated with recent changes: {value}"
    elif severity > Severity.MEDIUM and not correlated_changes:
        finding_type = "change_note"
        confidence = 0.60
        value = "no_changes_detected"
        hypothesis = "High severity incident, but no immediate change keywords detected in description."
    else: # severity <= MEDIUM
        finding_type = "change_note"
        confidence = 0.60
        value = ", ".join(correlated_changes) if correlated_changes else "no_changes_detected"
        hypothesis = "Lower severity incident, noting potential changes or lack thereof."

    summary = f"Change analysis for {task.incident_id}: {finding_type} - {value}"

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="change-agent",
        finding_type=finding_type,
        signal="change_tracking",
        value=value,
        confidence=confidence,
        hypothesis=hypothesis,
        summary=summary,
    )


def _extract_severity(task: TriageTask) -> Severity:
    """
    Extracts severity from the task description, identical to metrics_agent pattern.
    """
    if "CRITICAL" in task.description or "SEV-1" in task.description:
        return Severity.CRITICAL
    if "HIGH" in task.description or "spike" in task.description.lower():
        return Severity.HIGH
    if "MEDIUM" in task.description or "slow" in task.description.lower():
        return Severity.MEDIUM
    return Severity.LOW


def handle_task(envelope):
    """
    Handles incoming triage tasks, analyzes them, and publishes findings.
    """
    payload = envelope["payload"]
    task = TriageTask(**payload)
    
    if task.assigned_to != "@change-agent":
        return
        
    severity = _extract_severity(task)
    result = analyze(task, severity)

    logging.info(f"Publishing finding for task {task.task_id}: {result.finding_type}")
    band.publish("triage-findings", result.model_dump(), "change-agent")

    if severity <= Severity.MEDIUM:
        deliberation_message = {
            "sender": "change-agent",
            "content": (
                f"Low/Medium severity triage for {task.incident_id} complete. "
                f"Change correlation finding: {result.value}."
            ),
        }
        logging.info(f"Publishing deliberation for task {task.task_id}")
        band.publish("deliberation", deliberation_message, "change-agent")


def start():
    """
    Starts the Change Agent, subscribing to triage tasks and polling indefinitely.
    """
    logging.info("Change Agent starting...")
    band.subscribe("triage-tasks", handle_task)
    logging.info("Subscribed to 'triage-tasks'. Polling for messages...")
    while True:
        band.poll("triage-tasks")

if __name__ == "__main__":
    start()
