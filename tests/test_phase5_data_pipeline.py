"""
Phase 5 integration tests — verify agents produce data-driven findings
from real JSON/JSONL files instead of keyword-scanning descriptions.
"""
import pathlib
import pytest
from lib.models import TriageTask, Severity


BASE_DATA = pathlib.Path("data")


def _make_task(incident_id: str, agent: str, service: str = "") -> TriageTask:
    desc = f"Triage {incident_id}"
    if service:
        desc += f" on {service}"
    return TriageTask(
        task_id=f"t-{incident_id}",
        incident_id=incident_id,
        assigned_to=f"@{agent}",
        description=desc,
        data_path=str(BASE_DATA / incident_id) + "/",
        time_window="14:30-14:35",
    )


# ─── Metrics Agent ─────────────────────────────────────────────────────────────

class TestMetricsAgentDataPipeline:
    def test_inc001_detects_pool_exhaustion_anomaly(self):
        from agents.metrics_agent.main import analyze
        task = _make_task("inc-001", "metrics-agent")
        finding = analyze(task, Severity.HIGH)

        assert finding.finding_type == "anomaly"
        assert finding.confidence >= 0.88
        assert "pool" in finding.signal or "latency" in finding.signal
        assert finding.supporting_data["peak_p99_ms"] >= 2000
        assert finding.supporting_data["pool_pct"] >= 95
        assert finding.supporting_data["baseline_p99_ms"] == 120
        assert "pool" in finding.value or "latency" in finding.value.lower()

    def test_inc002_detects_elevated_latency_not_anomaly(self):
        from agents.metrics_agent.main import analyze
        task = _make_task("inc-002", "metrics-agent")
        finding = analyze(task, Severity.MEDIUM)

        assert finding.finding_type in ("anomaly", "observation")
        assert finding.supporting_data["peak_p99_ms"] == 380
        assert finding.supporting_data["pool_pct"] < 90

    def test_inc003_detects_total_outage(self):
        from agents.metrics_agent.main import analyze
        task = _make_task("inc-003", "metrics-agent")
        finding = analyze(task, Severity.CRITICAL)

        assert finding.finding_type == "anomaly"
        assert finding.confidence >= 0.90
        assert finding.supporting_data["error_rate_pct"] >= 42.0

    def test_fallback_when_no_data_path(self):
        from agents.metrics_agent.main import analyze
        task = TriageTask(
            task_id="t-fallback",
            incident_id="inc-fallback",
            assigned_to="@metrics-agent",
            description="CRITICAL: Something went wrong",
        )
        finding = analyze(task, Severity.CRITICAL)
        assert finding.signal == "simulated_analysis"
        assert finding.finding_type == "anomaly"

    def test_finding_has_required_fields(self):
        from agents.metrics_agent.main import analyze
        task = _make_task("inc-001", "metrics-agent")
        finding = analyze(task, Severity.HIGH)

        assert finding.finding_id
        assert finding.agent == "metrics-agent"
        assert finding.task_id == task.task_id
        assert 0.0 <= finding.confidence <= 1.0
        assert finding.hypothesis
        assert "inc-001" in finding.summary


# ─── Logs Agent ────────────────────────────────────────────────────────────────

class TestLogsAgentDataPipeline:
    def test_inc001_detects_connection_pool_exhaustion(self):
        from agents.logs_agent.main import analyze
        task = _make_task("inc-001", "logs-agent")
        finding = analyze(task, Severity.HIGH)

        assert finding.finding_type == "log_anomaly"
        assert finding.signal == "connection_pool_exhaustion"
        assert finding.confidence >= 0.85
        assert "ConnectionPoolExhaustedException" in finding.value
        assert finding.supporting_data["exception_counts"].get("ConnectionPoolExhaustedException", 0) == 5

    def test_inc002_detects_slow_queries_as_observation(self):
        from agents.logs_agent.main import analyze
        task = _make_task("inc-002", "logs-agent")
        finding = analyze(task, Severity.MEDIUM)

        assert finding.finding_type == "log_observation"
        assert "slow" in finding.signal or "warn" in finding.signal or "slow_queries" in finding.signal
        assert finding.supporting_data["total_errors"] == 0
        assert finding.supporting_data["total_warnings"] >= 5

    def test_inc003_detects_fatal_exceptions(self):
        from agents.logs_agent.main import analyze
        task = _make_task("inc-003", "logs-agent")
        finding = analyze(task, Severity.CRITICAL)

        assert finding.finding_type == "log_anomaly"
        assert finding.confidence >= 0.88
        assert finding.supporting_data["fatal_count"] >= 5
        assert "NullPointerException" in finding.supporting_data["exception_counts"]

    def test_fallback_when_no_data_path(self):
        from agents.logs_agent.main import analyze
        task = TriageTask(
            task_id="t-fallback",
            incident_id="inc-fallback",
            assigned_to="@logs-agent",
            description="timeout and error detected",
        )
        finding = analyze(task, Severity.LOW)
        assert finding.signal == "log_pattern_analysis"

    def test_finding_agent_is_logs_agent(self):
        from agents.logs_agent.main import analyze
        task = _make_task("inc-001", "logs-agent")
        finding = analyze(task, Severity.HIGH)
        assert finding.agent == "logs-agent"


# ─── Change Agent ──────────────────────────────────────────────────────────────

class TestChangeAgentDataPipeline:
    def test_inc001_finds_deploy_847_as_culprit(self):
        from agents.change_agent.main import analyze
        task = _make_task("inc-001", "change-agent")
        finding = analyze(task, Severity.HIGH)

        assert finding.finding_type == "change_correlation"
        assert finding.signal == "high_impact_deploy"
        assert "847" in finding.value
        assert finding.confidence >= 0.88
        assert finding.supporting_data["deploy_id"] == "847"
        assert "pool.maxSize" in finding.supporting_data["high_impact_keys"]
        assert finding.supporting_data["minutes_before_incident"] <= 5

    def test_inc001_diff_captures_pool_change(self):
        from agents.change_agent.main import analyze
        task = _make_task("inc-001", "change-agent")
        finding = analyze(task, Severity.HIGH)

        diff = finding.supporting_data["diff"]
        assert "pool.maxSize" in diff
        assert diff["pool.maxSize"]["before"] == 50
        assert diff["pool.maxSize"]["after"] == 10

    def test_inc002_reports_no_recent_changes(self):
        from agents.change_agent.main import analyze
        task = _make_task("inc-002", "change-agent")
        finding = analyze(task, Severity.MEDIUM)

        assert finding.signal == "no_recent_changes"
        assert finding.confidence >= 0.75

    def test_inc003_finds_vault_endpoint_change(self):
        from agents.change_agent.main import analyze
        task = _make_task("inc-003", "change-agent")
        finding = analyze(task, Severity.CRITICAL)

        assert finding.finding_type == "change_correlation"
        assert "302" in finding.value
        assert "vault" in finding.value.lower() or "vault" in str(finding.supporting_data).lower()

    def test_fallback_when_no_data_path(self):
        from agents.change_agent.main import analyze
        task = TriageTask(
            task_id="t-fallback",
            incident_id="inc-fallback",
            assigned_to="@change-agent",
            description="deploy and rollback happened",
        )
        finding = analyze(task, Severity.HIGH)
        assert finding.signal == "change_tracking"


# ─── Runbook Agent ─────────────────────────────────────────────────────────────

class TestRunbookAgentDataPipeline:
    def test_inc001_detects_stale_pool_size(self):
        from agents.runbook_agent.main import analyze
        task = _make_task("inc-001", "runbook-agent", "api-gateway")
        finding = analyze(task, Severity.HIGH, service="api-gateway")

        assert finding.finding_type == "runbook_match"
        assert finding.signal == "runbook_stale"
        assert "stale" in finding.value.lower()
        assert finding.supporting_data["days_since_update"] > 60
        assert len(finding.supporting_data["staleness_issues"]) >= 1

    def test_inc002_runbook_is_current(self):
        from agents.runbook_agent.main import analyze
        task = _make_task("inc-002", "runbook-agent", "user-service")
        finding = analyze(task, Severity.MEDIUM, service="user-service")

        assert finding.signal == "runbook_current"
        assert finding.supporting_data["staleness_issues"] == []

    def test_inc003_runbook_found_for_payment_service(self):
        from agents.runbook_agent.main import analyze
        task = _make_task("inc-003", "runbook-agent", "payment-service")
        finding = analyze(task, Severity.CRITICAL, service="payment-service")

        assert finding.finding_type == "runbook_match"
        assert finding.supporting_data["runbook_file"] == "payment-service.md"

    def test_fallback_when_no_data_path(self):
        from agents.runbook_agent.main import analyze
        task = TriageTask(
            task_id="t-fallback",
            incident_id="inc-fallback",
            assigned_to="@runbook-agent",
            description="rollback the service",
        )
        finding = analyze(task, Severity.HIGH)
        assert finding.signal == "runbook_analysis"


# ─── End-to-end: inc-001 full pipeline ─────────────────────────────────────────

class TestInc001FullPipeline:
    """Simulate the full inc-001 demo scenario through all 4 agents."""

    def test_all_four_agents_produce_findings_for_inc001(self):
        from agents.metrics_agent.main import analyze as metrics_analyze
        from agents.logs_agent.main import analyze as logs_analyze
        from agents.change_agent.main import analyze as change_analyze
        from agents.runbook_agent.main import analyze as runbook_analyze

        task = _make_task("inc-001", "metrics-agent", "api-gateway")
        m = metrics_analyze(task, Severity.HIGH)

        task.assigned_to = "@logs-agent"
        l = logs_analyze(task, Severity.HIGH)

        task.assigned_to = "@change-agent"
        c = change_analyze(task, Severity.HIGH)

        task.assigned_to = "@runbook-agent"
        r = runbook_analyze(task, Severity.HIGH, service="api-gateway")

        assert m.finding_type == "anomaly"
        assert l.signal == "connection_pool_exhaustion"
        assert c.supporting_data["deploy_id"] == "847"
        assert r.signal == "runbook_stale"

        confidences = [m.confidence, l.confidence, c.confidence, r.confidence]
        assert all(conf >= 0.75 for conf in confidences)

    def test_inc001_commander_verdict_is_resolved(self):
        """Full pipeline through Commander should produce a resolved verdict."""
        from agents.commander.main import handle_alert, handle_finding, incident_cache
        from agents.metrics_agent.main import analyze as metrics_analyze
        from agents.logs_agent.main import analyze as logs_analyze
        from agents.change_agent.main import analyze as change_analyze
        from agents.runbook_agent.main import analyze as runbook_analyze
        from lib.band_client import BandClientWrapper
        import agents.commander.main as commander_mod

        band = BandClientWrapper()
        original_band = commander_mod.band
        commander_mod.band = band
        incident_cache.clear()

        try:
            alert_payload = {
                "id": "alert-001",
                "title": "API Gateway Latency Spike",
                "description": "P99 latency spiked to 2450ms on api-gateway service",
                "severity": 3,
                "service": "api-gateway",
                "incident_id": "inc-001",
                "time_window": "14:30-14:35",
            }
            handle_alert({"payload": alert_payload})

            incident_id = "inc-001"
            assert incident_id in incident_cache

            task_base = _make_task(incident_id, "metrics-agent", "api-gateway")

            for agent_name, analyze_fn, kwargs in [
                ("metrics-agent", metrics_analyze, {"severity": Severity.HIGH}),
                ("logs-agent", logs_analyze, {"severity": Severity.HIGH}),
                ("change-agent", change_analyze, {"severity": Severity.HIGH}),
            ]:
                task_base.assigned_to = f"@{agent_name}"
                finding = analyze_fn(task_base, **kwargs)
                finding.agent = agent_name
                handle_finding({"payload": finding.model_dump()})

            task_base.assigned_to = "@runbook-agent"
            rb_finding = runbook_analyze(task_base, Severity.HIGH, service="api-gateway")
            rb_finding.agent = "runbook-agent"
            handle_finding({"payload": rb_finding.model_dump()})

            verdicts = band.message_queue.get("commander-verdict", [])
            assert len(verdicts) == 1
            payload = verdicts[0]["payload"]
            assert payload["status"] in ("resolved", "mitigating")
            assert payload["confidence"] > 0.5
            assert len(payload["evidence_ids"]) == 4

        finally:
            commander_mod.band = original_band
            incident_cache.clear()
