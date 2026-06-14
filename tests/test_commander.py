from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, Severity
from lib import evidence


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
        payload = verdicts[0]["payload"]
        assert "RESOLVED" in payload["verdict"]

        # 4. Check Phase 4 artifact fields are populated
        assert payload["incident_id"] == incident_id
        assert payload["status"] in ("resolved", "mitigating", "escalated")
        assert payload["severity"] == "SEV-1"  # CRITICAL alert -> SEV-1
        assert 0.0 <= payload["confidence"] <= 1.0
        assert len(payload["evidence_ids"]) == 4
        assert all(eid.startswith("EVD-") for eid in payload["evidence_ids"])
        assert f"## Postmortem: {incident_id}" in payload["draft_postmortem"]
        assert payload["status_page"]
        assert payload["deliberation_summary"] == {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 0}

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
        assert "Rollback" in str(payload["remediation"])
        assert "deployment" in payload["root_cause"].lower()
        assert "Rollback last deployment" in payload["draft_postmortem"]

    def test_deliberation_resolves_challenge_and_boosts_confidence(self):
        """A CHALLENGE resolved via CONNECT/AGREE should push the verdict to 'resolved'."""
        from agents.commander.main import handle_alert, handle_finding
        from lib.models import Finding

        # 1. Trigger Alert
        alert = IncidentAlert(id="alert-pool", title="API Gateway Latency Spike", description="P99 latency spike", severity=Severity.HIGH)
        handle_alert({"payload": alert.model_dump()})

        incident_id = list(self.band.message_queue["triage-tasks"])[0]["payload"]["incident_id"]

        # 2. Council deliberation: CHALLENGE resolved by AGREE + CONNECT, plus a SURFACE
        deliberation_messages = [
            {"sender": "logs-agent", "content": f"@metrics-agent CHALLENGE - no slow queries in logs for {incident_id}, it's pool exhaustion."},
            {"sender": "metrics-agent", "content": f"@logs-agent AGREE - pool usage at 98% confirms for {incident_id}."},
            {"sender": "change-agent", "content": f"@metrics-agent @logs-agent CONNECT - deploy #847 reduced pool size for {incident_id}."},
            {"sender": "runbook-agent", "content": f"SURFACE - runbook for {incident_id} is stale."},
        ]
        for msg in deliberation_messages:
            self.band.publish("deliberation", msg, msg["sender"])

        # 3. Simulate 4 high-confidence findings
        confidences = {"metrics-agent": 0.89, "logs-agent": 0.85, "change-agent": 0.80, "runbook-agent": 0.75}
        for agent, conf in confidences.items():
            finding = Finding(
                finding_id=f"f-{agent}",
                task_id="task-123",
                agent=agent,
                value="normal",
                confidence=conf,
                summary=f"Analysis for {incident_id}",
            )
            handle_finding({"payload": finding.model_dump()})

        # 4. Verdict reflects deliberation outcomes
        verdicts = self.band.message_queue.get("commander-verdict", [])
        payload = verdicts[0]["payload"]
        assert payload["deliberation_summary"] == {"agreed": 1, "challenged": 1, "connected": 1, "surfaced": 1}
        assert payload["status"] == "resolved"
        assert payload["confidence"] == 1.0

        # 5. Evidence trail covers findings + deliberation messages
        trail = evidence.store.get_evidence_trail(incident_id)
        assert len(trail) == 4 + 4 + 1  # 4 findings + 4 deliberation msgs + 1 verdict
        assert {e["type"] for e in trail} == {"finding", "deliberation", "verdict"}
