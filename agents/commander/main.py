import re
import uuid
import logging
from datetime import datetime, timezone
from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, TriageTask, Finding, CommanderVerdict
from lib import evidence, scorer, artifact_generator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

band = BandClientWrapper()

# In-memory state: incident_id -> { "findings": [], "expected": count, "alert": alert }
incident_cache = {}

INCIDENT_ID_PATTERN = re.compile(r"inc-[a-f0-9]+")


def _resolve_incident_id(text: str):
    """Extract an incident_id from free text, falling back to the most recent incident."""
    match = INCIDENT_ID_PATTERN.search(text or "")
    if match:
        return match.group(0)
    if incident_cache:
        return list(incident_cache.keys())[-1]
    return None


def _gather_deliberation(incident_id: str):
    """Read deliberation messages relevant to this incident from the Band queue."""
    messages = []
    for envelope in band.message_queue.get("deliberation", []):
        payload = envelope.get("payload", {})
        match = INCIDENT_ID_PATTERN.search(payload.get("content", ""))
        if match and match.group(0) != incident_id:
            continue
        messages.append(payload)
    return messages


def generate_verdict(incident_id: str):
    """Synthesizes agent findings + deliberation into a final verdict and artifact."""
    state = incident_cache.get(incident_id)
    if not state:
        return

    findings = state["findings"]
    alert = state["alert"]

    # Cross-domain correlation
    has_log_errors = any("error" in f.value.lower() or "5xx" in f.value.lower() for f in findings if f.agent == "logs-agent")
    has_recent_deploy = any("deploy" in f.value.lower() or "release" in f.value.lower() for f in findings if f.agent == "change-agent")
    has_metrics_anomaly = any(f.finding_type == "anomaly" for f in findings if f.agent == "metrics-agent")

    if has_log_errors and has_recent_deploy:
        verdict_text = f"CRITICAL: Deployment correlation found for {alert.title}. Recent changes are causing service errors."
        root_cause = f"Recent deployment change correlates with service errors reported in logs for {alert.title}."
        remediation = ["Rollback last deployment", "Check container logs for specific crash reason"]
    elif has_metrics_anomaly:
        verdict_text = f"WARNING: Metrics anomaly detected for {alert.title} without clear change correlation."
        root_cause = f"Metrics anomaly detected for {alert.title} with no corresponding change correlation."
        remediation = ["Scale up resources", "Inspect underlying infrastructure health"]
    else:
        verdict_text = f"RESOLVED: Triage complete for {alert.title}. No critical cross-domain correlation found."
        root_cause = f"No critical cross-domain correlation found for {alert.title}; system within normal operating parameters."
        remediation = ["Monitor service closely", "Close incident if symptoms subside"]

    # Evidence trail: record every finding
    evidence_ids = []
    for finding in findings:
        record = evidence.store.store(incident_id, finding.agent, "finding", finding.model_dump())
        evidence_ids.append(record.id)

    # Deliberation: record + summarize for scoring
    deliberation_msgs = _gather_deliberation(incident_id)
    for msg in deliberation_msgs:
        evidence.store.store(incident_id, msg.get("sender", "unknown"), "deliberation", msg)

    deliberation_summary = scorer.summarize_deliberation(deliberation_msgs)
    confidence = scorer.compute_confidence(findings, deliberation_summary)
    status = scorer.gate(confidence)

    severity = artifact_generator.map_severity(alert.severity)
    draft_postmortem = artifact_generator.generate_postmortem(
        incident_id=incident_id,
        alert=alert,
        severity=severity,
        root_cause=root_cause,
        remediation=remediation,
        evidence_ids=evidence_ids,
    )
    status_page = artifact_generator.generate_status_page(status, alert, root_cause)

    verdict = CommanderVerdict(
        incident_id=incident_id,
        status=status,
        verdict=verdict_text,
        root_cause=root_cause,
        severity=severity,
        confidence=round(confidence, 2),
        remediation=remediation,
        draft_postmortem=draft_postmortem,
        status_page=status_page,
        evidence_ids=evidence_ids,
        deliberation_summary=deliberation_summary,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    evidence.store.store(incident_id, "commander", "verdict", verdict.model_dump())
    band.publish("commander-verdict", verdict.model_dump(), "commander")
    logging.info(
        f"Published verdict for {incident_id}: {verdict_text} "
        f"(status={status}, confidence={confidence:.2f})"
    )


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

    target_inc_id = _resolve_incident_id(finding.summary)

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
