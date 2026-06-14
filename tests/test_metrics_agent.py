from lib.band_client import BandClientWrapper
from lib.models import TriageTask, Severity


class TestMetricsAgent:
    def setup_method(self):
        self.band = BandClientWrapper()
        import agents.metrics_agent.main as metrics_mod
        self._original_band = metrics_mod.band
        metrics_mod.band = self.band

    def teardown_method(self):
        import agents.metrics_agent.main as metrics_mod
        metrics_mod.band = self._original_band

    def test_critical_severity_returns_anomaly(self):
        """Given TriageTask with severity=CRITICAL, analyzer returns anomaly."""
        from agents.metrics_agent.main import analyze

        task = TriageTask(
            task_id="t1", incident_id="inc-001",
            assigned_to="@metrics-agent",
            description="CRITICAL: Full outage",
        )
        result = analyze(task, Severity.CRITICAL)
        assert result.finding_type == "anomaly"

    def test_low_severity_returns_observation(self):
        """Given TriageTask with severity=LOW, analyzer returns observation."""
        from agents.metrics_agent.main import analyze

        task = TriageTask(
            task_id="t2", incident_id="inc-002",
            assigned_to="@metrics-agent",
            description="INFO: Minor latency",
        )
        result = analyze(task, Severity.LOW)
        assert result.finding_type == "observation"

    def test_high_severity_high_confidence(self):
        """Given TriageTask with severity=HIGH, Finding has high confidence."""
        from agents.metrics_agent.main import analyze

        task = TriageTask(
            task_id="t3", incident_id="inc-003",
            assigned_to="@metrics-agent",
            description="HIGH: Latency spike",
        )
        result = analyze(task, Severity.HIGH)
        assert result.confidence >= 0.8

    def test_low_severity_triggers_deliberation(self):
        """Given severity=LOW, agent publishes to deliberation."""
        from agents.metrics_agent.main import handle_task

        task = TriageTask(
            task_id="t4", incident_id="inc-004",
            assigned_to="@metrics-agent",
            description="INFO: Minor issue",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 1
        assert deliberation_msgs[0]["sender"] == "metrics-agent"

    def test_critical_severity_no_deliberation(self):
        """Given severity=CRITICAL, agent does NOT publish to deliberation."""
        from agents.metrics_agent.main import handle_task

        task = TriageTask(
            task_id="t5", incident_id="inc-005",
            assigned_to="@metrics-agent",
            description="CRITICAL: Service down",
        )
        envelope = {"payload": task.model_dump(), "sender": "commander"}
        handle_task(envelope)

        deliberation_msgs = self.band.message_queue.get("deliberation", [])
        assert len(deliberation_msgs) == 0
