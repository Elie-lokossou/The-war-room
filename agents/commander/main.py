import uuid
import logging
from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, TriageTask, Finding, CommanderVerdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

band = BandClientWrapper()

# In-memory state: incident_id -> { "findings": [], "expected": count, "alert": alert }
incident_cache = {}


def generate_verdict(incident_id: str):
    """Synthesizes agent findings into a final verdict."""
    state = incident_cache.get(incident_id)
    if not state:
        return

    findings = state["findings"]
    alert = state["alert"]
    
    # Simple Synthesis Logic
    has_log_errors = any("error" in f.value.lower() or "5xx" in f.value.lower() for f in findings if f.agent == "logs-agent")
    has_recent_deploy = any("deploy" in f.value.lower() or "release" in f.value.lower() for f in findings if f.agent == "change-agent")
    has_metrics_anomaly = any(f.finding_type == "anomaly" for f in findings if f.agent == "metrics-agent")
    
    actions = []
    if has_log_errors and has_recent_deploy:
        verdict_text = f"CRITICAL: Deployment correlation found for {alert.title}. Recent changes are causing service errors."
        actions = ["Rollback last deployment", "Check container logs for specific crash reason"]
    elif has_metrics_anomaly:
        verdict_text = f"WARNING: Metrics anomaly detected for {alert.title} without clear change correlation."
        actions = ["Scale up resources", "Inspect underlying infrastructure health"]
    else:
        verdict_text = f"RESOLVED: Triage complete for {alert.title}. No critical cross-domain correlation found."
        actions = ["Monitor service closely", "Close incident if symptoms subside"]

    verdict = CommanderVerdict(
        incident_id=incident_id,
        verdict=verdict_text,
        actions_to_take=actions
    )
    
    band.publish("commander-verdict", verdict.model_dump(), "commander")
    logging.info(f"Published verdict for {incident_id}: {verdict_text}")


def handle_alert(envelope):
    payload = envelope["payload"]
    alert = IncidentAlert(**payload)
    incident_id = f"inc-{str(uuid.uuid4())[:8]}"
    
    expected_agents = ["metrics-agent", "logs-agent", "change-agent", "runbook-agent"]
    
    # Initialize cache for this incident
    incident_cache[incident_id] = {
        "findings": [],
        "expected": len(expected_agents),
        "alert": alert
    }

    for agent_label in [f"@{a}" for a in expected_agents]:
        task = TriageTask(
            task_id=str(uuid.uuid4())[:8],
            incident_id=incident_id,
            assigned_to=agent_label,
            description=f"Triage {alert.title}: {alert.description}",
        )
        band.publish("triage-tasks", task.model_dump(), "commander")
        band.send_message(
            "triage-tasks",
            f"{agent_label} triage task assigned",
            mentions=[agent_label],
        )


def handle_finding(envelope):
    payload = envelope["payload"]
    finding = Finding(**payload)
    
    # Extract incident_id from finding summary or other metadata
    # The summary follows the pattern: "Agent analysis for inc-XXXX: ..."
    target_inc_id = None
    import re
    match = re.search(r"inc-[a-f0-9]+", finding.summary)
    if match:
        target_inc_id = match.group(0)
    
    # Fallback for tests or missing summary patterns
    if not target_inc_id and incident_cache:
        target_inc_id = list(incident_cache.keys())[-1] # Use the most recent incident

    if target_inc_id and target_inc_id in incident_cache:
        state = incident_cache[target_inc_id]
        state["findings"].append(finding)
        logging.info(f"Commander received finding from {finding.agent} for {target_inc_id} ({len(state['findings'])}/{state['expected']})")
        
        if len(state["findings"]) == state["expected"]:
            generate_verdict(target_inc_id)


def start():
    band.subscribe("incident-events", handle_alert)
    band.subscribe("triage-findings", handle_finding)
    logging.info("Commander started. Subscribed to incident-events and triage-findings.")
    while True:
        band.poll("incident-events")
        band.poll("triage-findings")
