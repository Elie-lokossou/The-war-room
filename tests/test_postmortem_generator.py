import pytest
from datetime import datetime, timezone
from lib.postmortem_generator import generate_postmortem
from lib.models import CommanderVerdict, Finding, Severity

def test_generate_postmortem():
    verdict = CommanderVerdict(
        incident_id="inc-test-123",
        status="resolved",
        verdict="Verdict summary details",
        root_cause="Bad config deployment",
        severity="SEV-2",
        confidence=0.9,
        remediation=["Rollback last deployment", "Monitor service closely"],
        draft_postmortem="Initial draft",
        status_page="Status page update",
        timestamp=datetime.now(timezone.utc).isoformat(),
        deliberation_summary={"AGREE": 2, "CHALLENGE": 1, "CONNECT": 0, "SURFACE": 0}
    )
    
    findings = [
        Finding(
            finding_id="evd-1",
            task_id="t-1",
            agent="metrics-agent",
            finding_type="anomaly",
            signal="latency_spike",
            summary="Metrics spike detected"
        ),
        Finding(
            finding_id="evd-2",
            task_id="t-2",
            agent="logs-agent",
            finding_type="log_anomaly",
            signal="error_crash",
            summary="Connection reset exceptions"
        )
    ]
    
    deliberation_log = [
        {"sender": "metrics-agent", "content": "I see high latency"},
        {"sender": "logs-agent", "content": "I see matching errors"}
    ]
    
    markdown = generate_postmortem(verdict, findings, deliberation_log, total_mttr=4.2)
    
    assert "# Postmortem: inc-test-123" in markdown
    assert "## Summary" in markdown
    assert "Verdict summary details" in markdown
    assert "Bad config deployment" in markdown
    assert "MTTR: 4.2s" in markdown
    assert "metrics-agent" in markdown
    assert "logs-agent" in markdown
    assert "- **AGREE**: 2" in markdown
    assert "- **CHALLENGE**: 1" in markdown
