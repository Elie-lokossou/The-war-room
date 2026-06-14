from lib.evidence import EvidenceStore


class TestEvidenceStore:
    def setup_method(self):
        self.store = EvidenceStore()

    def test_store_generates_prefixed_evidence_id(self):
        record = self.store.store("inc-001", "metrics-agent", "finding", {"value": "normal"})
        assert record.id.startswith("EVD-MT-")
        assert record.incident_id == "inc-001"
        assert record.agent == "metrics-agent"
        assert record.type == "finding"

    def test_unknown_agent_uses_default_prefix(self):
        record = self.store.store("inc-001", "human", "deliberation", {"content": "@ChangeAgent check the deploy"})
        assert record.id.startswith("EVD-EV-")

    def test_get_evidence_returns_stored_record(self):
        record = self.store.store("inc-001", "logs-agent", "finding", {"value": "errors"})
        fetched = self.store.get_evidence(record.id)
        assert fetched is not None
        assert fetched.id == record.id

    def test_get_by_incident_filters_correctly(self):
        self.store.store("inc-001", "metrics-agent", "finding", {})
        self.store.store("inc-002", "logs-agent", "finding", {})
        self.store.store("inc-001", "change-agent", "finding", {})

        inc_001 = self.store.get_by_incident("inc-001")
        assert len(inc_001) == 2
        assert all(e.incident_id == "inc-001" for e in inc_001)

    def test_get_evidence_trail_is_chronological_dicts(self):
        first = self.store.store("inc-001", "metrics-agent", "finding", {"order": 1})
        second = self.store.store("inc-001", "logs-agent", "finding", {"order": 2})

        trail = self.store.get_evidence_trail("inc-001")
        assert [e["id"] for e in trail] == [first.id, second.id]
        assert all(isinstance(e, dict) for e in trail)

    def test_get_evidence_trail_empty_for_unknown_incident(self):
        assert self.store.get_evidence_trail("inc-does-not-exist") == []
