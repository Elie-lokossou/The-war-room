import json
import uuid
import logging
import pathlib
from datetime import datetime, timezone
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

_IMPACT_KEYS = {"pool.maxSize", "pool.minIdle", "vault.endpoint", "vault.client_init",
                "heap", "replicas", "timeout", "rate_limit"}


def _minutes_before_incident(deploy_ts: str, incident_ts: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        d = datetime.strptime(deploy_ts, fmt).replace(tzinfo=timezone.utc)
        i = datetime.strptime(incident_ts, fmt).replace(tzinfo=timezone.utc)
        return (i - d).total_seconds() / 60.0
    except Exception:
        return float("inf")


def _analyze_from_file(task: TriageTask) -> Finding:
    data_file = pathlib.Path(task.data_path) / "changes" / "deploys.json"
    data = json.loads(data_file.read_text())
    deploys = data.get("deploys", [])
    incident_start = data.get("incident_start", "")

    correlated = []
    for deploy in deploys:
        if not incident_start:
            correlated.append(deploy)
            continue
        minutes = _minutes_before_incident(deploy.get("timestamp", ""), incident_start)
        if 0 <= minutes <= 30:
            correlated.append((deploy, minutes))

    if not incident_start:
        correlated = [(d, None) for d in deploys]

    if not correlated:
        return Finding(
            finding_id=str(uuid.uuid4())[:8],
            task_id=task.task_id,
            agent="change-agent",
            finding_type="change_note",
            signal="no_recent_changes",
            value="no_changes_in_30min_window",
            confidence=0.80,
            hypothesis="No deployments or config changes in the 30-minute window before the incident",
            summary=f"Change analysis for {task.incident_id}: no recent changes",
        )

    closest_deploy, minutes = correlated[0]
    deploy_id = closest_deploy.get("deploy_id", "unknown")
    description = closest_deploy.get("description", "")
    diff = closest_deploy.get("diff", {})
    timestamp = closest_deploy.get("timestamp", "")

    high_impact = [k for k in diff if k in _IMPACT_KEYS]
    diff_summary = "; ".join(
        f"{k}: {v['before']} → {v['after']}" for k, v in diff.items() if isinstance(v, dict)
    )

    if high_impact:
        finding_type = "change_correlation"
        confidence = 0.90
        signal = "high_impact_deploy"
        hypothesis = (
            f"Deploy #{deploy_id} at {timestamp} ({minutes:.0f}min before incident) "
            f"changed high-impact config: {diff_summary}"
        )
    else:
        finding_type = "change_correlation"
        confidence = 0.70
        signal = "recent_deploy"
        hypothesis = (
            f"Deploy #{deploy_id} at {timestamp} ({minutes:.0f}min before incident): {description}"
        )

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="change-agent",
        finding_type=finding_type,
        signal=signal,
        value=f"deploy #{deploy_id} at {timestamp}, diff: {diff_summary or 'see supporting_data'}",
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Change analysis for {task.incident_id}: {finding_type} — deploy #{deploy_id}",
        supporting_data={
            "deploy_id": deploy_id,
            "deploy_timestamp": timestamp,
            "minutes_before_incident": round(minutes, 1) if minutes is not None else None,
            "diff": diff,
            "high_impact_keys": high_impact,
            "total_correlated_deploys": len(correlated),
        },
    )


def _analyze_from_description(task: TriageTask, severity: Severity) -> Finding:
    keywords = ["deploy", "release", "config", "change", "rollback", "update", "migration"]
    correlated = [kw for kw in keywords if kw in task.description.lower()]

    if severity > Severity.MEDIUM and correlated:
        finding_type = "change_correlation"
        confidence = 0.80
        value = ", ".join(correlated)
        hypothesis = f"High severity incident correlated with recent changes: {value}"
    elif severity > Severity.MEDIUM:
        finding_type = "change_note"
        confidence = 0.60
        value = "no_changes_detected"
        hypothesis = "High severity incident, but no change keywords detected in description."
    else:
        finding_type = "change_note"
        confidence = 0.60
        value = ", ".join(correlated) if correlated else "no_changes_detected"
        hypothesis = "Lower severity incident, noting potential changes or lack thereof."

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="change-agent",
        finding_type=finding_type,
        signal="change_tracking",
        value=value,
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Change analysis for {task.incident_id}: {finding_type} - {value}",
    )


def analyze(task: TriageTask, severity: Severity) -> Finding:
    if task.data_path:
        data_file = pathlib.Path(task.data_path) / "changes" / "deploys.json"
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

    if task.assigned_to != "@change-agent":
        return

    severity = _extract_severity(task)
    result = analyze(task, severity)

    logging.info(f"Publishing finding for task {task.task_id}: {result.finding_type}")
    band.publish("triage-findings", result.model_dump(), "change-agent")

    if severity <= Severity.MEDIUM:
        band.publish(
            "deliberation",
            {
                "sender": "change-agent",
                "content": (
                    f"Low/Medium severity triage for {task.incident_id} complete. "
                    f"Change correlation finding: {result.value}."
                ),
            },
            "change-agent",
        )


def start():
    logging.info("Change Agent starting...")
    band.subscribe("triage-tasks", handle_task)
    logging.info("Subscribed to 'triage-tasks'. Polling for messages...")
    while True:
        band.poll("triage-tasks")


if __name__ == "__main__":
    start()
