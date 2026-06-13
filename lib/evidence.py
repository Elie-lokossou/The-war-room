import uuid
from typing import Dict, Optional
from .models import Evidence

class EvidenceStore:
    def __init__(self):
        self._store: Dict[str, Evidence] = {}

    def generate_id(self, prefix: str) -> str:
        """Generate Evidence ID (EVD-{prefix}-{uuid_short})"""
        uuid_short = str(uuid.uuid4())[:8]
        return f"EVD-{prefix}-{uuid_short}"

    def add_evidence(self, evidence: Evidence) -> None:
        self._store[evidence.id] = evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        return self._store.get(evidence_id)

# Agent Prefixes
AGENT_PREFIXES = {
    "commander": "CM",
    "metrics-agent": "MT",
    "logs-agent": "LG",
    "change-agent": "CH",
    "runbook-agent": "RB"
}

# Global in-memory store
store = EvidenceStore()
