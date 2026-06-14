from lib.models import IncidentAlert, Severity
from lib import artifact_generator


def _alert(severity):
    return IncidentAlert(
        id="alert-001",
        title="API Gateway Latency Spike",
        description="P99 latency spiked to 2450ms on api-gateway service",
        severity=severity,
    )


class TestMapSeverity:
    def test_critical_maps_to_sev1(self):
        assert artifact_generator.map_severity(Severity.CRITICAL) == "SEV-1"

    def test_high_maps_to_sev2(self):
        assert artifact_generator.map_severity(Severity.HIGH) == "SEV-2"

    def test_medium_and_low_map_to_sev3(self):
        assert artifact_generator.map_severity(Severity.MEDIUM) == "SEV-3"
        assert artifact_generator.map_severity(Severity.LOW) == "SEV-3"


class TestGeneratePostmortem:
    def test_includes_all_sections(self):
        postmortem = artifact_generator.generate_postmortem(
            incident_id="inc-001",
            alert=_alert(Severity.HIGH),
            severity="SEV-2",
            root_cause="Deploy #847 reduced connection pool from 50 to 10",
            remediation=["Rollback deploy #847", "Increase pool size to 50"],
            evidence_ids=["EVD-MT-aaaaaaaa", "EVD-CH-bbbbbbbb"],
        )

        assert "## Postmortem: inc-001" in postmortem
        assert "**Severity**: SEV-2" in postmortem
        assert "Deploy #847 reduced connection pool from 50 to 10" in postmortem
        assert "1. [ ] Rollback deploy #847" in postmortem
        assert "2. [ ] Increase pool size to 50" in postmortem
        assert "EVD-MT-aaaaaaaa, EVD-CH-bbbbbbbb" in postmortem

    def test_handles_no_evidence(self):
        postmortem = artifact_generator.generate_postmortem(
            incident_id="inc-002",
            alert=_alert(Severity.LOW),
            severity="SEV-3",
            root_cause="No correlation found",
            remediation=["Monitor service closely"],
            evidence_ids=[],
        )
        assert "**Evidence Trail**: none" in postmortem


class TestGenerateStatusPage:
    def test_resolved_status(self):
        page = artifact_generator.generate_status_page("resolved", _alert(Severity.HIGH), "Connection pool exhaustion")
        assert page.startswith("Resolved:")
        assert "Connection pool exhaustion" in page

    def test_mitigating_status(self):
        page = artifact_generator.generate_status_page("mitigating", _alert(Severity.HIGH), "Connection pool exhaustion")
        assert page.startswith("Investigating:")

    def test_escalated_status(self):
        page = artifact_generator.generate_status_page("escalated", _alert(Severity.CRITICAL), "Unknown")
        assert page.startswith("Escalated:")
        assert "on-call" in page
