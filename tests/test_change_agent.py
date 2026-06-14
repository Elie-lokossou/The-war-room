from lib.band_client import BandClientWrapper
from lib.models import TriageTask, Severity


class TestChangeAgent:
    def setup_method(self):
        self.band = BandClientWrapper()
        import agents.change_agent.main as change_mod
        self._original_band = change_mod.band
        change_mod.band = self.band

    def teardown_method(self):
        import agents.change_agent.main as change_mod
        change_mod.band = self._original_band

    def test_high_severity_with_keywords_returns_change_correlation(self):
        """Given TriageTask with severity=HIGH and change keywords, returns change_correlation."""
        from agents.change_agent.main import analyze

        task = TriageTask(
            task_id="t1", incident_id="inc-001",
            assigned_to="@change-agent",
            description="HIGH: Latency spike after deploy",
        )
        result = analyze(task, Severity.HIGH)
        assert result.finding_type == "change_correlation"

    def test_low_severity_returns_change_note(self):
        """Given TriageTask with severity=LOW, analyzer returns change_note."""
        from agents.change_agent.main import analyze

        task = TriageTask(
            task_id="t2", incident_id="inc-002",
            assigned_to="@change-agent",
            description="INFO: Minor performance dip",
        )
        result = analyze(task, Severity.LOW)
        assert result.finding_type == "change_note"

    def test_high_severity_no_keywords_returns_change_note(self):
        """Given severity=HIGH but no change keywords, returns change_note."""
        from agents.change_agent.main import analyze

        task = TriageTask(
            task_id="t3", incident_id="inc-003",
            assigned_to="@change-agent",
            description="HIGH: Random error spike",
        )
        result = analyze(task, Severity.HIGH)
        assert result.finding_type == "change_note"

    def test_low_severity_triggers_deliberation(self):
        """Given severity=LOW, agent publishes to deliberation."""
        from agents.change_agent.main import handle_task

        task = TriageTask(
            task_id="t4", incident_id="inc-004",
            assigned_to="@change-agent",
            description="INFO: Routine check",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 1
        assert deliberation_msgs[0]["sender"] == "change-agent"

    def test_critical_severity_no_deliberation(self):
        """Given severity=CRITICAL, agent does NOT publish to deliberation."""
        from agents.change_agent.main import handle_task

        task = TriageTask(
            task_id="t5", incident_id="inc-005",
            assigned_to="@change-agent",
            description="CRITICAL: Full outage",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 0
