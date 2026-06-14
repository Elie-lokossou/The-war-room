from lib.band_client import BandClientWrapper
from lib.models import TriageTask, Severity


class TestRunbookAgent:
    def setup_method(self):
        self.band = BandClientWrapper()
        import agents.runbook_agent.main as runbook_mod
        self._original_band = runbook_mod.band
        runbook_mod.band = self.band

    def teardown_method(self):
        import agents.runbook_agent.main as runbook_mod
        runbook_mod.band = self._original_band

    def test_high_severity_with_keyword_returns_runbook_match(self):
        """Given TriageTask with severity > MEDIUM and runbook keyword, analyzer returns runbook_match."""
        from agents.runbook_agent.main import analyze

        task = TriageTask(
            task_id="t1", incident_id="inc-001",
            assigned_to="@runbook-agent",
            description="HIGH: Service degraded, check runbook for mitigation",
        )
        result = analyze(task, Severity.HIGH)
        assert result.finding_type == "runbook_match"
        assert result.confidence == 0.75
        assert "mitigation" in result.value

    def test_low_severity_with_keyword_returns_runbook_note(self):
        """Given TriageTask with severity <= MEDIUM and runbook keyword, analyzer returns runbook_note."""
        from agents.runbook_agent.main import analyze

        task = TriageTask(
            task_id="t2", incident_id="inc-002",
            assigned_to="@runbook-agent",
            description="INFO: Minor issue, see if there's a playbook",
        )
        result = analyze(task, Severity.LOW)
        assert result.finding_type == "runbook_note"
        assert result.confidence == 0.55
        assert "no_runbook_match" in result.value # It's low severity, so it defaults to no_runbook_match

    def test_high_severity_no_keyword_returns_runbook_note(self):
        """Given TriageTask with severity > MEDIUM but no runbook keyword, analyzer returns runbook_note."""
        from agents.runbook_agent.main import analyze

        task = TriageTask(
            task_id="t3", incident_id="inc-003",
            assigned_to="@runbook-agent",
            description="CRITICAL: Database connection lost",
        )
        result = analyze(task, Severity.CRITICAL)
        assert result.finding_type == "runbook_note"
        assert result.confidence == 0.55
        assert result.value == "no_runbook_match"

    def test_low_severity_triggers_deliberation(self):
        """Given severity=LOW, agent publishes to deliberation."""
        from agents.runbook_agent.main import handle_task

        task = TriageTask(
            task_id="t4", incident_id="inc-004",
            assigned_to="@runbook-agent",
            description="INFO: Small glitch, nothing critical.",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 1
        assert deliberation_msgs[0]["sender"] == "runbook-agent"
