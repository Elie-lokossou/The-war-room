from typing import List
from .models import IncidentAlert, Severity

SEVERITY_MAP = {
    Severity.CRITICAL: "SEV-1",
    Severity.HIGH: "SEV-2",
    Severity.MEDIUM: "SEV-3",
    Severity.LOW: "SEV-3",
}

STATUS_LABELS = {
    "resolved": "Resolved",
    "mitigating": "Investigating",
    "escalated": "Escalated",
}


def map_severity(severity: Severity) -> str:
    """Map internal Severity enum to a SEV-1/SEV-2/SEV-3 status-page label."""
    return SEVERITY_MAP.get(severity, "SEV-3")


def generate_postmortem(
    incident_id: str,
    alert: IncidentAlert,
    severity: str,
    root_cause: str,
    remediation: List[str],
    evidence_ids: List[str],
) -> str:
    """Render a draft postmortem in markdown from incident evidence."""
    action_items = "\n".join(f"{i + 1}. [ ] {item}" for i, item in enumerate(remediation))
    evidence_line = ", ".join(evidence_ids) if evidence_ids else "none"

    return (
        f"## Postmortem: {incident_id}\n"
        f"**Severity**: {severity}\n"
        f"**Root Cause**: {root_cause}\n"
        f"**Trigger**: {alert.title}\n"
        f"**Detection**: Automated alert via #incident-events\n"
        f"**Impact**: {alert.description}\n"
        f"**Resolution**: {'; '.join(remediation)}\n"
        f"**Action Items**:\n{action_items}\n"
        f"**Evidence Trail**: {evidence_line}\n"
    )


def generate_status_page(status: str, alert: IncidentAlert, root_cause: str) -> str:
    """Render a one-line public status page update."""
    label = STATUS_LABELS.get(status, status.title())

    if status == "resolved":
        action_taken = f"root cause identified — {root_cause}"
    elif status == "mitigating":
        action_taken = "mitigation in progress, monitoring for recovery"
    else:
        action_taken = "escalated to on-call for manual investigation"

    return f"{label}: {alert.title} — {action_taken}"
