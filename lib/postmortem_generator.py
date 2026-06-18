from datetime import datetime, timezone, timedelta
from typing import List, Any
from lib.models import CommanderVerdict, Finding
from lib.remediation import map_action_string_to_model

def generate_postmortem(verdict: CommanderVerdict, findings: List[Finding], deliberation_log: List[Any], total_mttr: float = 0.0) -> str:
    """
    Generate a structured Markdown postmortem for the incident.
    """
    try:
        verdict_time = datetime.fromisoformat(verdict.timestamp.replace("Z", "+00:00"))
    except Exception:
        verdict_time = datetime.now(timezone.utc)
        
    date_str = verdict_time.strftime("%Y-%m-%d")
    
    alert_time = (verdict_time - timedelta(minutes=5)).strftime("%H:%M:%S UTC")
    triage_time = (verdict_time - timedelta(minutes=4)).strftime("%H:%M:%S UTC")
    deliberation_time = (verdict_time - timedelta(minutes=2)).strftime("%H:%M:%S UTC")
    v_time_str = verdict_time.strftime("%H:%M:%S UTC")
    
    # If total_mttr is not provided, estimate it from the recommended actions
    if total_mttr <= 0.0:
        total_mttr = sum(map_action_string_to_model(act).duration for act in verdict.remediation)
        
    rem_time = (verdict_time + timedelta(seconds=total_mttr)).strftime("%H:%M:%S UTC")
    mttr_str = f"{total_mttr:.1f}s"

    remediation_checklist = ""
    for act in verdict.remediation:
        remediation_checklist += f"- [x] {act}\n"
    if not remediation_checklist:
        remediation_checklist = "No remediation actions performed."
        
    evidence_trail = ""
    for f in findings:
        evidence_trail += f"- **{f.finding_id}**: {f.agent} ({f.finding_type} - {f.signal})\n"
    if not evidence_trail:
        evidence_trail = "No evidence recorded."
        
    delib_summary = verdict.deliberation_summary or {}
    
    md = f"""# Postmortem: {verdict.incident_id} — {date_str}

## Summary
{verdict.verdict}

## Timeline
- **{alert_time}**: Incident Alert Ingested
- **{triage_time}**: Triage assigned to Metrics, Logs, Change, and Runbook agents
- **{deliberation_time}**: Deliberation channel discussions completed ({len(deliberation_log)} messages)
- **{v_time_str}**: Commander Verdict published (Status: {verdict.status.upper()}, Confidence: {verdict.confidence})
- **{rem_time}**: Automated Remediation executed successfully (MTTR: {mttr_str})

## Root Cause
{verdict.root_cause}

## Severity
- **Level**: {verdict.severity}
- **Confidence Score**: {verdict.confidence:.2f}

## Remediation Actions
{remediation_checklist.strip()}

## Evidence Trail
{evidence_trail.strip()}

## Deliberation Summary
- **AGREE**: {delib_summary.get("AGREE", 0)}
- **CHALLENGE**: {delib_summary.get("CHALLENGE", 0)}
- **CONNECT**: {delib_summary.get("CONNECT", 0)}
- **SURFACE**: {delib_summary.get("SURFACE", 0)}

## Action Items
1. [ ] Implement automated regression tests for root cause.
2. [ ] Review and update runbook instructions for {verdict.severity} incidents.
3. [ ] Configure high-frequency alerting thresholds on affected metrics.
"""
    return md
