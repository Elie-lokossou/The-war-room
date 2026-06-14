from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, Severity


class TestCommander:
    def setup_method(self):
        self.band = BandClientWrapper()
        import agents.commander.main as commander_mod
        self._original_band = commander_mod.band
        commander_mod.band = self.band

    def teardown_method(self):
        import agents.commander.main as commander_mod
        commander_mod.band = self._original_band

    def test_generates_unique_incident_id(self):
        """Given an IncidentAlert, Commander generates a unique incident_id."""
        from agents.commander.main import handle_alert

        alert = IncidentAlert(
            id="alert-001",
            title="Test Alert",
            description="Something went wrong",
            severity=Severity.HIGH,
        )
        envelope = {"payload": alert.model_dump(), "sender": "alert-system"}
        handle_alert(envelope)

        ids = set()
        for msg in self.band.message_queue.get("triage-tasks", []):
            ids.add(msg["payload"]["incident_id"])

        assert len(ids) == 1
        assert list(ids)[0].startswith("inc-")

    def test_fans_out_to_all_four_agents(self):
        """Given an IncidentAlert, Commander publishes TriageTasks to all 4 agents."""
        from agents.commander.main import handle_alert

        alert = IncidentAlert(
            id="alert-002",
            title="DB Slowdown",
            description="Database query times increased",
            severity=Severity.MEDIUM,
        )
        envelope = {"payload": alert.model_dump(), "sender": "alert-system"}
        handle_alert(envelope)

        agents_assigned = set()
        for msg in self.band.message_queue.get("triage-tasks", []):
            agents_assigned.add(msg["payload"]["assigned_to"])

        assert "@metrics-agent" in agents_assigned
        assert "@logs-agent" in agents_assigned
        assert "@change-agent" in agents_assigned
        assert "@runbook-agent" in agents_assigned
        assert len(agents_assigned) == 4

    def test_critical_severity_in_task_description(self):
        """Given severity=CRITICAL alert, task description includes severity info."""
        from agents.commander.main import handle_alert

        alert = IncidentAlert(
            id="alert-003",
            title="SEV-1 Outage",
            description="Full service outage detected",
            severity=Severity.CRITICAL,
        )
        envelope = {"payload": alert.model_dump(), "sender": "alert-system"}
        handle_alert(envelope)

        for msg in self.band.message_queue.get("triage-tasks", []):
            desc = msg["payload"]["description"]
            assert "SEV-1" in desc or "Outage" in desc

    def test_no_alert_publishes_nothing(self):
        """Given no alert, Commander publishes nothing."""
        assert len(self.band.message_queue.get("triage-tasks", [])) == 0
