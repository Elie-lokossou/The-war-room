# Codebase Reference

Quick reference for what each file does and what its key functions are.

---

## `lib/models.py`

All Pydantic v2 schemas shared across the system.

| Class | Key fields |
|-------|-----------|
| `Severity` | `IntEnum`: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4 |
| `Evidence` | `id`, `incident_id`, `agent`, `type` ("finding"\|"deliberation"\|"verdict"), `content`, `timestamp` |
| `IncidentAlert` | `id`, `title`, `description`, `severity: Severity` |
| `TriageTask` | `task_id`, `incident_id`, `assigned_to`, `description`, `data_path=""`, `time_window=""` |
| `Finding` | `finding_id`, `task_id`, `agent`, `finding_type`, `signal`, `value`, `confidence`, `hypothesis`, `summary`, `evidence[]`, `supporting_data{}` |
| `DeliberationMessage` | `message_id`, `sender`, `content` |
| `CommanderVerdict` | `incident_id`, `status`, `verdict`, `root_cause`, `severity` (SEV-1/2/3), `confidence`, `remediation[]`, `draft_postmortem`, `status_page`, `evidence_ids[]`, `deliberation_summary{}`, `timestamp` |

---

## `lib/band_client.py` — `BandClientWrapper`

Mock Band SDK. In production this wraps the real Band WebSocket API.

| Method | What it does |
|--------|-------------|
| `subscribe(channel, handler)` | Register a callback for messages on a channel |
| `publish(channel, message_dict, sender)` | Push message to in-memory queue; logs to console |
| `poll(channel)` | Drain queued messages, calling all registered handlers |
| `send_message(room_id, message, mentions)` | Log an @mention message (no-op in mock) |
| `create_room(name)` / `add_participant(room, agent)` | Log only (no-op) |

**Internal state**:
- `self.subscribers: Dict[str, List[Callable]]` — channel → handler list
- `self.message_queue: Dict[str, List[dict]]` — channel → buffered envelopes

---

## `lib/evidence.py` — `EvidenceStore`

In-memory record of every event in an incident's lifecycle.

| Method | What it does |
|--------|-------------|
| `store(incident_id, agent, type, content)` | Create + persist an `Evidence` record; returns the record |
| `get_by_incident(incident_id)` | All evidence for one incident |
| `get_evidence_trail(incident_id)` | Sorted chronological list of `model_dump()` dicts |
| `generate_id(prefix)` | Returns `EVD-{prefix}-{uuid8}` |

**Global**: `store = EvidenceStore()` — one instance for the whole process.

**Agent prefixes**: CM, MT, LG, CH, RB

---

## `lib/scorer.py`

| Function | What it does |
|----------|-------------|
| `summarize_deliberation(messages)` | Count AGREE/CHALLENGE/CONNECT/SURFACE in message contents; returns `{agreed, challenged, connected, surfaced}` |
| `compute_confidence(findings, deliberation_summary)` | Weighted average + deliberation bonuses/penalties; clamped to [0.0, 1.0] |
| `gate(confidence)` | `"resolved"` / `"mitigating"` / `"escalated"` |

---

## `lib/artifact_generator.py`

| Function | What it does |
|----------|-------------|
| `map_severity(severity: Severity)` | `CRITICAL→SEV-1`, `HIGH→SEV-2`, `MEDIUM/LOW→SEV-3` |
| `generate_postmortem(incident_id, alert, severity, root_cause, remediation, evidence_ids)` | Returns multi-line markdown postmortem |
| `generate_status_page(status, alert, root_cause)` | Returns one-line public status update string |

---

## `agents/commander/main.py`

| Function | What it does |
|----------|-------------|
| `handle_alert(envelope)` | Parses `IncidentAlert`; generates `incident_id`; fans out 4 `TriageTask`s |
| `handle_finding(envelope)` | Appends finding to `incident_cache`; calls `generate_verdict()` when count == 4 |
| `generate_verdict(incident_id)` | Cross-domain correlation → evidence store → deliberation → scoring → `CommanderVerdict` → publish |
| `_resolve_incident_id(text)` | Extracts `inc-{hex}` from free text; falls back to last incident |
| `_gather_deliberation(incident_id)` | Reads deliberation messages from `band.message_queue["deliberation"]` |
| `start()` | Subscribes to `incident-events` and `triage-findings`; poll loop |

**Global state**: `incident_cache: dict` — `{incident_id: {findings[], expected: int, alert: IncidentAlert}}`

---

## `agents/{metrics,logs,change,runbook}_agent/main.py`

All 4 follow the same pattern:

| Function | What it does |
|----------|-------------|
| `analyze(task, severity)` | Returns a `Finding` — **currently keyword-based, Phase 5 replaces this** |
| `_extract_severity(task)` | Parses description for CRITICAL/HIGH/MEDIUM/LOW keywords |
| `handle_task(envelope)` | Filters by `assigned_to`, calls `analyze()`, publishes to `triage-findings` |
| `start()` | Subscribes to `triage-tasks`, poll loop |

**Phase 5 change**: `analyze()` in each agent will read from `task.data_path` instead of scanning `task.description`.

---

## `tests/`

| File | Tests |
|------|-------|
| `test_commander.py` | 6 tests: unique ID, fan-out, severity, no-alert, full verdict, CHALLENGE deliberation |
| `test_metrics_agent.py` | 5 tests |
| `test_logs_agent.py` | 5 tests |
| `test_change_agent.py` | 5 tests |
| `test_runbook_agent.py` | 4 tests |
| `test_scorer.py` | Confidence scoring unit tests |
| `test_evidence.py` | EvidenceStore unit tests |
| `test_artifact_generator.py` | Postmortem + status page generation |

Run all tests: `pytest` from project root.

---

## `data/inc-001/alert.json`

```json
{
  "id": "alert-001",
  "title": "API Gateway Latency Spike",
  "description": "P99 latency spiked to 2450ms on api-gateway service",
  "severity": 3
}
```

Note: `severity: 3` maps to `Severity.HIGH` (IntEnum value).
