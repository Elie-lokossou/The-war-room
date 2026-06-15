import re
import uuid
import pathlib
from datetime import date
from lib.band_client import BandClientWrapper
from lib.models import Finding, TriageTask, Severity

band = BandClientWrapper()

_STALE_DAYS_THRESHOLD = 60
_REFERENCE_DATE = date(2026, 6, 16)

_VALUE_PATTERNS = [
    (r"pool\.maxSize\s*[|:=\s]+\s*(\d+)", "pool.maxSize"),
    (r"pool[:\s]+max\s+size\s+\**(\d+)", "pool.maxSize"),
    (r"heap[\s_-]*max[\s=:|]+\s*(\d+)\s*[gG]", "jvm.heap_max_gb"),
]

_RUNBOOK_KEYWORDS = ["runbook", "mitigation", "playbook", "remediation", "rollback", "restart", "failover"]


def _find_runbook(data_path: str, service: str) -> pathlib.Path | None:
    runbook_dir = pathlib.Path(data_path) / "runbooks"
    if not runbook_dir.exists():
        return None
    for candidate in [f"{service}.md", f"{service}-runbook.md", "runbook.md"]:
        p = runbook_dir / candidate
        if p.exists():
            return p
    md_files = list(runbook_dir.glob("*.md"))
    return md_files[0] if md_files else None


def _days_since_update(content: str) -> int | None:
    match = re.search(r"last\s+updated[:\s*]+(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)
    if not match:
        return None
    try:
        updated = date.fromisoformat(match.group(1))
        return (_REFERENCE_DATE - updated).days
    except ValueError:
        return None


def _extract_documented_values(content: str) -> list[dict]:
    found = []
    for pattern, config_key in _VALUE_PATTERNS:
        for m in re.findall(pattern, content, re.IGNORECASE):
            try:
                found.append({"config_key": config_key, "documented_value": int(m)})
            except ValueError:
                pass
    return found


def _analyze_from_file(task: TriageTask, service: str) -> Finding:
    runbook_path = _find_runbook(task.data_path, service)
    if not runbook_path:
        return None

    content = runbook_path.read_text()
    sections = [s.strip() for s in content.split("\n## ") if s.strip()]
    section_count = len(sections)
    last_updated = ""
    for line in content.splitlines():
        if "last updated" in line.lower():
            last_updated = line.strip()
            break

    days_old = _days_since_update(content)
    is_stale = days_old is not None and days_old > _STALE_DAYS_THRESHOLD
    documented_values = _extract_documented_values(content)

    if is_stale:
        finding_type = "runbook_match"
        confidence = 0.82
        signal = "runbook_stale"
        doc_summary = (
            ", ".join(f"{d['config_key']}={d['documented_value']}" for d in documented_values)
            or "no config values found"
        )
        hypothesis = (
            f"Runbook '{runbook_path.name}' is STALE: last updated {days_old} days ago "
            f"(threshold: {_STALE_DAYS_THRESHOLD} days). "
            f"Documented config: {doc_summary}. "
            f"Verify these values reflect current system state before following procedures."
        )
        value = f"stale: {days_old} days old, docs: {doc_summary}"
        recommended_action = f"Review and update '{runbook_path.name}' — {days_old} days without update"
        staleness_issues = [{"days_old": days_old, "documented_values": documented_values}]
    else:
        finding_type = "runbook_match"
        confidence = 0.75
        signal = "runbook_current"
        age_str = f"{days_old} days old" if days_old is not None else "age unknown"
        hypothesis = (
            f"Runbook '{runbook_path.name}' found with {section_count} sections. "
            f"Procedures appear current ({age_str}). {last_updated}"
        )
        value = f"runbook_current, sections={section_count}, {age_str}"
        recommended_action = "Follow runbook procedures as documented"
        staleness_issues = []

    return Finding(
        finding_id=str(uuid.uuid4())[:8],
        task_id=task.task_id,
        agent="runbook-agent",
        finding_type=finding_type,
        signal=signal,
        value=value,
        confidence=confidence,
        hypothesis=hypothesis,
        summary=f"Runbook analysis for {task.incident_id}: {finding_type} — {signal}",
        supporting_data={
            "runbook_file": runbook_path.name,
            "section_count": section_count,
            "last_updated": last_updated,
            "days_since_update": days_old,
            "staleness_issues": staleness_issues,
            "documented_values": documented_values,
            "recommended_action": recommended_action,
        },
    )


def _analyze_from_description(task: TriageTask, severity: Severity) -> Finding:
    matched = [kw for kw in _RUNBOOK_KEYWORDS if kw in task.description.lower()]

    if severity > Severity.MEDIUM and matched:
        finding_type = "runbook_match"
        confidence = 0.75
        value = ", ".join(matched)
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
        supporting_data={"recommended_action": recommended_action},
    )


def analyze(task: TriageTask, severity: Severity, service: str = "") -> Finding:
    if task.data_path:
        svc = service or "unknown"
        result = _analyze_from_file(task, svc)
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


def _extract_service(task: TriageTask) -> str:
    for word in task.description.split():
        if word.endswith("-service") or word.endswith("_service"):
            return word.rstrip(".,;:")
    return "unknown"


def handle_task(envelope):
    payload = envelope["payload"]
    task = TriageTask(**payload)

    if task.assigned_to != "@runbook-agent":
        return

    severity = _extract_severity(task)
    service = _extract_service(task)
    result = analyze(task, severity, service)
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
