from lib.band_client import BandClientWrapper
from lib.models import TriageTask, Severity


class TestLogsAgent:
    def setup_method(self):
        self.band = BandClientWrapper()
        import agents.logs_agent.main as logs_mod
        self._original_band = logs_mod.band
        logs_mod.band = self.band

    def teardown_method(self):
        import agents.logs_agent.main as logs_mod
        logs_mod.band = self._original_band

    def test_critical_severity_returns_log_anomaly(self):
        """Given TriageTask with severity=CRITICAL, analyzer returns log_anomaly."""
        from agents.logs_agent.main import analyze

        task = TriageTask(
            task_id="t1", incident_id="inc-001",
            assigned_to="@logs-agent",
            description="CRITICAL: Exception in request handler",
        )
        result = analyze(task, Severity.CRITICAL)
        assert result.finding_type == "log_anomaly"

    def test_low_severity_returns_log_observation(self):
        """Given TriageTask with severity=LOW, analyzer returns log_observation."""
        from agents.logs_agent.main import analyze

        task = TriageTask(
            task_id="t2", incident_id="inc-002",
            assigned_to="@logs-agent",
            description="INFO: Normal operation log",
        )
        result = analyze(task, Severity.LOW)
        assert result.finding_type == "log_observation"

    def test_high_severity_high_confidence(self):
        """Given TriageTask with severity=HIGH, Finding has high confidence."""
        from agents.logs_agent.main import analyze

        task = TriageTask(
            task_id="t3", incident_id="inc-003",
            assigned_to="@logs-agent",
            description="HIGH: Error rate spike detected",
        )
        result = analyze(task, Severity.HIGH)
        assert result.confidence >= 0.8

    def test_low_severity_triggers_deliberation(self):
        """Given severity=LOW, agent publishes to deliberation."""
        from agents.logs_agent.main import handle_task

        task = TriageTask(
            task_id="t4", incident_id="inc-004",
            assigned_to="@logs-agent",
            description="INFO: Routine log check",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 1
        assert deliberation_msgs[0]["sender"] == "logs-agent"

    def test_critical_severity_no_deliberation(self):
        """Given severity=CRITICAL, agent does NOT publish to deliberation."""
        from agents.logs_agent.main import handle_task

        task = TriageTask(
            task_id="t5", incident_id="inc-005",
            assigned_to="@logs-agent",
            description="CRITICAL: Service crash detected",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 0
