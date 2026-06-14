import pytest
from lib.models import Finding
from lib import scorer


def _finding(agent, confidence):
    return Finding(
        finding_id=f"f-{agent}",
        task_id="t1",
        agent=agent,
        value="normal",
        confidence=confidence,
        summary="Analysis for inc-test0001",
    )


class TestSummarizeDeliberation:
    def test_counts_each_protocol_verb(self):
        messages = [
            {"sender": "logs-agent", "content": "CHALLENGE - no slow queries"},
            {"sender": "metrics-agent", "content": "AGREE - pool usage confirms"},
            {"sender": "change-agent", "content": "CONNECT - deploy aligns with spike"},
            {"sender": "runbook-agent", "content": "SURFACE - runbook is stale"},
        ]
        summary = scorer.summarize_deliberation(messages)
        assert summary == {"agreed": 1, "challenged": 1, "connected": 1, "surfaced": 1}

    def test_no_messages_returns_zero_counts(self):
        assert scorer.summarize_deliberation([]) == {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 0}

    def test_message_without_protocol_verb_is_ignored(self):
        messages = [{"sender": "metrics-agent", "content": "Low severity triage complete."}]
        summary = scorer.summarize_deliberation(messages)
        assert summary == {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 0}


class TestComputeConfidence:
    def test_no_findings_no_deliberation_is_zero(self):
        assert scorer.compute_confidence([]) == 0.0

    def test_weighted_average_without_deliberation(self):
        findings = [
            _finding("metrics-agent", 0.8),
            _finding("logs-agent", 0.8),
            _finding("change-agent", 0.8),
            _finding("runbook-agent", 0.8),
        ]
        # All agents at 0.8, no deliberation -> deliberation slot excluded entirely
        confidence = scorer.compute_confidence(findings)
        assert confidence == pytest.approx(0.8, abs=1e-6)

    def test_resolved_challenge_increases_confidence(self):
        findings = [
            _finding("metrics-agent", 0.89),
            _finding("logs-agent", 0.85),
            _finding("change-agent", 0.80),
            _finding("runbook-agent", 0.75),
        ]
        deliberation = {"agreed": 1, "challenged": 1, "connected": 1, "surfaced": 1}
        confidence = scorer.compute_confidence(findings, deliberation)
        assert confidence == 1.0  # clamped after bonuses

    def test_unresolved_challenge_decreases_confidence(self):
        findings = [_finding("metrics-agent", 0.9)]
        without_challenge = scorer.compute_confidence(findings, {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 0})
        with_unresolved_challenge = scorer.compute_confidence(findings, {"agreed": 0, "challenged": 1, "connected": 0, "surfaced": 0})
        assert with_unresolved_challenge < without_challenge

    def test_surface_without_connect_penalizes(self):
        findings = [_finding("metrics-agent", 0.9)]
        baseline = scorer.compute_confidence(findings, {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 0})
        with_surface = scorer.compute_confidence(findings, {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 1})
        assert with_surface < baseline

    def test_confidence_is_clamped_between_zero_and_one(self):
        findings = [_finding("metrics-agent", 1.0)]
        deliberation = {"agreed": 5, "challenged": 1, "connected": 5, "surfaced": 0}
        assert scorer.compute_confidence(findings, deliberation) == 1.0


class TestGate:
    def test_high_confidence_is_resolved(self):
        assert scorer.gate(0.80) == "resolved"
        assert scorer.gate(0.95) == "resolved"

    def test_mid_confidence_is_mitigating(self):
        assert scorer.gate(0.50) == "mitigating"
        assert scorer.gate(0.79) == "mitigating"

    def test_low_confidence_is_escalated(self):
        assert scorer.gate(0.49) == "escalated"
        assert scorer.gate(0.0) == "escalated"
