from typing import Dict, List, Optional
from .models import Finding

# Base weights for the weighted-average confidence (sum to 1.0)
AGENT_WEIGHTS: Dict[str, float] = {
    "metrics-agent": 0.25,
    "logs-agent": 0.25,
    "change-agent": 0.25,
    "runbook-agent": 0.15,
}
DELIBERATION_WEIGHT = 0.10

# Deliberation bonuses / penalties
CHALLENGE_RESOLVED_BONUS = 0.10
CHALLENGE_UNRESOLVED_PENALTY = -0.10
CONNECT_BONUS = 0.05
AGREE_BONUS = 0.02
SURFACE_WITHOUT_ACTION_PENALTY = -0.05

# Gate thresholds
RESOLVED_THRESHOLD = 0.80
MITIGATING_THRESHOLD = 0.50

_VERB_TO_KEY = {
    "CHALLENGE": "challenged",
    "CONNECT": "connected",
    "SURFACE": "surfaced",
    "AGREE": "agreed",
}


def summarize_deliberation(messages: List[dict]) -> Dict[str, int]:
    """Count AGREE/CHALLENGE/CONNECT/SURFACE protocol verbs across deliberation messages."""
    summary = {"agreed": 0, "challenged": 0, "connected": 0, "surfaced": 0}
    for message in messages:
        content = (message.get("content") or "").upper()
        for verb, key in _VERB_TO_KEY.items():
            if verb in content:
                summary[key] += 1
                break
    return summary


def compute_confidence(findings: List[Finding], deliberation_summary: Optional[Dict[str, int]] = None) -> float:
    """Weighted-average agent confidence, adjusted by deliberation outcomes."""
    deliberation_summary = deliberation_summary or {}

    weighted_sum = 0.0
    weight_total = 0.0
    for finding in findings:
        weight = AGENT_WEIGHTS.get(finding.agent, 0.0)
        weighted_sum += finding.confidence * weight
        weight_total += weight

    # Deliberation only contributes its weight slot when it actually happened —
    # otherwise it would dilute the average as if it were a confirmed zero-confidence input.
    if any(deliberation_summary.values()):
        weighted_sum += DELIBERATION_WEIGHT
        weight_total += DELIBERATION_WEIGHT

    score = weighted_sum / weight_total if weight_total else 0.0

    challenged = deliberation_summary.get("challenged", 0)
    connected = deliberation_summary.get("connected", 0)
    agreed = deliberation_summary.get("agreed", 0)
    surfaced = deliberation_summary.get("surfaced", 0)

    if challenged:
        challenge_resolved = connected > 0 or agreed > 0
        score += CHALLENGE_RESOLVED_BONUS if challenge_resolved else CHALLENGE_UNRESOLVED_PENALTY

    score += connected * CONNECT_BONUS
    score += agreed * AGREE_BONUS

    if surfaced and not connected:
        score += SURFACE_WITHOUT_ACTION_PENALTY

    return max(0.0, min(1.0, score))


def gate(confidence: float) -> str:
    """Map a confidence score to an incident status."""
    if confidence >= RESOLVED_THRESHOLD:
        return "resolved"
    if confidence >= MITIGATING_THRESHOLD:
        return "mitigating"
    return "escalated"
