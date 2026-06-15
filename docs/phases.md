# Build Phases

## Status Summary

| Phase | Name | Status | Est. |
|-------|------|--------|------|
| 0 | Scaffold + Band setup | DONE | — |
| 1 | Commander triage | DONE | — |
| 2 | Analysis agents (all 4) | DONE | — |
| 3 | Commander verdict | DONE (part of Phase 4) | — |
| 4 | Evidence + scoring + artifact system | DONE | — |
| 5 | Real data pipeline | **TODO** | ~3h |
| 6 | Dashboard & presentation | **TODO** | ~8h |

---

## Phase 1 — Commander Triage ✅

**Goal**: Ingest alerts, generate `incident_id`, fan out triage tasks.

**What's built**:
- `handle_alert(envelope)` — parses `IncidentAlert`, generates `inc-{uuid8}` ID
- Fans out `TriageTask` to 4 agents via `triage-tasks` channel with @mentions
- `handle_finding(envelope)` — collects findings; triggers `generate_verdict()` when all 4 arrive
- 4 tests: unique ID, fan-out count, severity in description, no-alert baseline

**Key files**: `agents/commander/main.py`

**Channels**: subscribes `incident-events`, publishes `triage-tasks`

---

## Phase 2 — Analysis Agents ✅

**Goal**: Each agent receives triage tasks, analyzes its domain, publishes findings.

**What's built** (all 4 agents follow identical pattern):

| Agent | High-sev finding | Low-sev finding | Signal |
|-------|-----------------|-----------------|--------|
| Metrics | `anomaly` (0.9) | `observation` (0.7) | `simulated_analysis` |
| Logs | `log_anomaly` (0.85) | `log_observation` (0.65) | `log_pattern_analysis` |
| Change | `change_correlation` (0.8) | `change_note` (0.6) | `change_tracking` |
| Runbook | `runbook_match` (0.75) | `runbook_note` (0.55) | `runbook_analysis` |

**Pattern** (same for all agents):
1. Subscribe to `triage-tasks`
2. `_extract_severity()` parses description keywords (CRITICAL, HIGH, MEDIUM, LOW / spike, slow)
3. `analyze()` returns a `Finding` based on severity
4. Publish finding to `triage-findings`
5. If severity ≤ MEDIUM → also publish to `deliberation` (low-sev note)

**⚠️ Current limitation**: All analysis is keyword-scanning of the description string. Phase 5 replaces this with real data file reads.

**Key files**: `agents/{metrics,logs,change,runbook}_agent/main.py`

---

## Phase 3 + 4 — Commander Verdict + Evidence System ✅

**Goal**: Collect findings, compute confidence, publish structured verdict + artifacts.

**What's built**:

`generate_verdict(incident_id)` does:
1. Cross-domain correlation check (logs errors + recent deploy → critical; metrics anomaly only → warning; none → resolved)
2. Stores every finding in `EvidenceStore` with prefixed IDs (`EVD-MT-xxx`, etc.)
3. Reads deliberation messages from Band queue, summarizes AGREE/CHALLENGE/CONNECT/SURFACE counts
4. Calls `scorer.compute_confidence(findings, deliberation_summary)` with weights + bonuses/penalties
5. Gates confidence: `≥0.80` resolved, `0.50–0.79` mitigating, `<0.50` escalated
6. Generates `draft_postmortem` (markdown) and `status_page` (one-liner) via `artifact_generator`
7. Publishes full `CommanderVerdict` to `commander-verdict`

**Key files**: `agents/commander/main.py`, `lib/evidence.py`, `lib/scorer.py`, `lib/artifact_generator.py`

---

## Phase 5 — Real Data Pipeline 🔴 TODO

**Goal**: Replace keyword-scanning with actual data file reads so agents produce realistic, data-driven findings.

**Assigned to**: Team member (you)

**What needs building**:

### 1. Data files (3 scenarios)

```
data/
├── inc-001/           API Gateway latency spike (THE DEMO scenario)
│   ├── alert.json     ✅ exists
│   ├── metrics/
│   │   └── snapshots.json   P99: 120ms→2450ms at 14:31, pool 98%, error_rate 3.2%
│   ├── logs/
│   │   └── events.jsonl     20 lines: 5× ConnectionPoolExhaustedException at 14:31
│   ├── changes/
│   │   └── deploys.json     Deploy #847 at 14:30: pool.maxSize 50→10
│   └── runbooks/
│       └── api-gateway.md   Runbook still says pool size 50 (stale)
├── inc-002/           Low severity — brief latency spike, self-resolved
└── inc-003/           Critical — full outage, failover executed
```

### 2. Agent analysis logic updates

Each agent's `analyze()` currently keyword-scans `task.description`. Replace with:

- **Metrics Agent**: read `data/{incident_id}/metrics/snapshots.json`, compare P99 to baseline, detect pool saturation
- **Logs Agent**: read `data/{incident_id}/logs/events.jsonl`, count error types by time bucket, extract exception class names
- **Change Agent**: read `data/{incident_id}/changes/deploys.json`, correlate deploy timestamps to incident start time
- **Runbook Agent**: read `data/{incident_id}/runbooks/{service}.md`, detect stale procedures (pool size mismatch, etc.)

### 3. `TriageTask` must carry `data_path` and `time_window`

`TriageTask.data_path` and `TriageTask.time_window` fields already exist in `lib/models.py` — Commander just needs to populate them when fanning out:

```python
task = TriageTask(
    ...,
    data_path=f"data/{incident_id}/",
    time_window="14:30-14:35",
)
```

### Metrics data format

```json
{
  "incident_id": "inc-001",
  "baseline_window": "14:00-14:30",
  "incident_window": "14:31-14:35",
  "snapshots": [
    {
      "timestamp": "2026-06-12T14:31:00Z",
      "p50_latency_ms": 450,
      "p95_latency_ms": 1200,
      "p99_latency_ms": 2450,
      "error_rate_pct": 3.2,
      "cpu_pct": 45,
      "memory_pct": 72,
      "connection_pool_usage_pct": 98,
      "baseline_p99_ms": 120
    }
  ]
}
```

### Logs data format (JSONL — one JSON object per line)

```json
{"timestamp": "2026-06-12T14:31:15Z", "level": "ERROR", "service": "api-gateway", "message": "ConnectionPoolExhaustedException: no connections available", "trace_id": "abc123", "exception": "ConnectionPoolExhaustedException"}
{"timestamp": "2026-06-12T14:31:22Z", "level": "WARN", "service": "api-gateway", "message": "Query timeout after 2000ms", "trace_id": "def456"}
```

### Changes data format

```json
{
  "incident_id": "inc-001",
  "deploys": [
    {
      "deploy_id": "847",
      "timestamp": "2026-06-12T14:30:00Z",
      "description": "Update connection pool configuration",
      "diff": {"pool.maxSize": {"before": 50, "after": 10}},
      "author": "deploy-bot"
    }
  ]
}
```

---

## Phase 6 — Dashboard & Presentation 🔴 TODO

**Goal**: Make it look like a real product. This is what judges see.

**What needs building**:
- Streamlit or React dashboard (real-time: alert → agents working → verdict)
- Side panel: `#deliberation` live feed showing agents "talking"
- Architecture diagram (Mermaid or draw.io)
- Slide deck (7 slides — see `docs/demo.md`)
- 90-second video recording

**Key dependency**: Phase 5 must be done first so agents produce realistic output.

**Time estimate**: ~5h dashboard, ~3h presentation materials

---

## Dependency Chain

```
Phase 0 (done)
    └── Phase 1 (done)
            └── Phase 2 (done)
                    └── Phase 3+4 (done)
                            ├── Phase 5 (TODO — you)
                            └── Phase 6 (TODO — after Phase 5)
```
