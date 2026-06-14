from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, Severity


class TestCommander:
    def setup_method(self):
        self.band = BandClientWrapper()
        import agents.commander.main as commander_mod
        self._original_band = commander_mod.band
        commander_mod.band = self.band
        commander_mod.incident_cache.clear()

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

    def test_generates_verdict_after_all_findings(self):
        """Commander should publish a verdict once all 4 expected findings are received."""
        from agents.commander.main import handle_alert, handle_finding
        from lib.models import Finding

        # 1. Trigger Alert
        alert = IncidentAlert(id="alert-999", title="Test Outage", description="Test", severity=Severity.CRITICAL)
        handle_alert({"payload": alert.model_dump()})
        
        # Get the incident_id
        incident_id = list(self.band.message_queue["triage-tasks"])[0]["payload"]["incident_id"]

        # 2. Simulate 4 Findings
        agents = ["metrics-agent", "logs-agent", "change-agent", "runbook-agent"]
        for agent in agents:
            finding = Finding(
                finding_id=f"f-{agent}",
                task_id="task-123",
                agent=agent,
                value="normal",
                summary=f"Analysis for {incident_id}"
            )
            handle_finding({"payload": finding.model_dump()})

        # 3. Check Verdict
        verdicts = self.band.message_queue.get("commander-verdict", [])
        assert len(verdicts) > 0
        assert "RESOLVED" in verdicts[0]["payload"]["verdict"]

    def test_generates_critical_verdict_on_deployment_error(self):
        """Commander should suggest rollback if logs report errors AND change agent reports a deploy."""
        from agents.commander.main import handle_alert, handle_finding
        from lib.models import Finding

        # 1. Trigger Alert
        alert = IncidentAlert(id="alert-deploy-fail", title="API Crash", description="500 errors", severity=Severity.CRITICAL)
        handle_alert({"payload": alert.model_dump()})
        
        # Get the incident_id from the tasks
        incident_id = list(self.band.message_queue["triage-tasks"])[0]["payload"]["incident_id"]

        # 2. Simulate Findings
        # Logs reports 500 errors
        f_logs = Finding(finding_id="f-logs", task_id="t1", agent="logs-agent", value="5xx_errors", summary=f"Logs analysis for {incident_id}")
        # Change reports a deployment
        f_change = Finding(finding_id="f-change", task_id="t2", agent="change-agent", value="recent_deploy", summary=f"Change analysis for {incident_id}")
        # Others report normal
        f_metrics = Finding(finding_id="f-metrics", task_id="t3", agent="metrics-agent", value="normal", summary=f"Metrics analysis for {incident_id}")
        f_runbook = Finding(finding_id="f-runbook", task_id="t4", agent="runbook-agent", value="normal", summary=f"Runbook analysis for {incident_id}")

        for f in [f_logs, f_change, f_metrics, f_runbook]:
            handle_finding({"payload": f.model_dump()})

        # 3. Verify Critical Verdict
        verdicts = self.band.message_queue.get("commander-verdict", [])
        assert len(verdicts) > 0
        payload = verdicts[0]["payload"]
        assert "CRITICAL" in payload["verdict"]
        assert "Rollback" in str(payload["actions_to_take"])
