import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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

    def store(self, incident_id: str, agent: str, type: str, content: Any) -> Evidence:
        """Create, persist, and return a new Evidence record for an incident."""
        prefix = AGENT_PREFIXES.get(agent, DEFAULT_PREFIX)
        record = Evidence(
            id=self.generate_id(prefix),
            incident_id=incident_id,
            agent=agent,
            type=type,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.add_evidence(record)
        return record

    def get_by_incident(self, incident_id: str) -> List[Evidence]:
        return [e for e in self._store.values() if e.incident_id == incident_id]

    def get_evidence_trail(self, incident_id: str) -> List[Dict[str, Any]]:
        """Chronological audit trail of all evidence for an incident."""
        records = sorted(self.get_by_incident(incident_id), key=lambda e: e.timestamp)
        return [record.model_dump() for record in records]

# Agent Prefixes
AGENT_PREFIXES = {
    "commander": "CM",
    "metrics-agent": "MT",
    "metrics_agent": "MT",
    "logs-agent": "LG",
    "logs_agent": "LG",
    "change-agent": "CH",
    "change_agent": "CH",
    "runbook-agent": "RB",
    "runbook_agent": "RB",
}
DEFAULT_PREFIX = "EV"

# Global in-memory store
store = EvidenceStore()
