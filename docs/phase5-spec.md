# Phase 5 — Real Data Pipeline (Your Assignment)

## Goal

Replace all keyword-scanning mock analysis with agents that read actual JSON/JSONL data files. When Phase 5 is done, agents produce findings that reference real timestamps, real error messages, and real deploy diffs — not inferred from the alert description text.

---

## Current State (What Agents Do Now)

Every agent's `analyze()` does this:

```python
def _extract_severity(task: TriageTask) -> Severity:
    if "CRITICAL" in task.description: return Severity.CRITICAL
    if "spike" in task.description.lower(): return Severity.HIGH
    ...

def analyze(task, severity) -> Finding:
    # Returns a canned finding based on severity bucket
    finding_type = "anomaly" if severity > MEDIUM else "observation"
    confidence = 0.9 if finding_type == "anomaly" else 0.7
    return Finding(..., signal="simulated_analysis", value=f"severity={severity.name}")
```

This is fine for unit tests but produces fake output. The demo needs agents to say "P99 latency is 2450ms vs baseline 120ms" and "Deploy #847 at 14:30 changed pool.maxSize 50→10".

---

## What You Need to Build

### Step 1 — Create data files

Location: `data/inc-001/` (demo scenario) + `data/inc-002/`, `data/inc-003/` (supporting scenarios)

#### `data/inc-001/metrics/snapshots.json`
```json
{
  "incident_id": "inc-001",
  "baseline_window": "14:00-14:30",
  "incident_window": "14:31-14:35",
  "snapshots": [
    {
      "timestamp": "2026-06-12T14:29:00Z",
      "p50_latency_ms": 65,
      "p95_latency_ms": 110,
      "p99_latency_ms": 120,
      "error_rate_pct": 0.1,
      "cpu_pct": 42,
      "memory_pct": 68,
      "connection_pool_usage_pct": 42,
      "baseline_p99_ms": 120
    },
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

#### `data/inc-001/logs/events.jsonl`
One JSON object per line:
```jsonl
{"timestamp": "2026-06-12T14:30:50Z", "level": "INFO", "service": "api-gateway", "message": "Request processed in 118ms", "trace_id": "aaa001"}
{"timestamp": "2026-06-12T14:31:15Z", "level": "ERROR", "service": "api-gateway", "message": "ConnectionPoolExhaustedException: no connections available", "trace_id": "bbb001", "exception": "ConnectionPoolExhaustedException"}
{"timestamp": "2026-06-12T14:31:22Z", "level": "ERROR", "service": "api-gateway", "message": "ConnectionPoolExhaustedException: no connections available", "trace_id": "bbb002", "exception": "ConnectionPoolExhaustedException"}
{"timestamp": "2026-06-12T14:31:28Z", "level": "WARN", "service": "api-gateway", "message": "Query timeout after 2000ms", "trace_id": "ccc001"}
{"timestamp": "2026-06-12T14:31:35Z", "level": "ERROR", "service": "api-gateway", "message": "ConnectionPoolExhaustedException: no connections available", "trace_id": "bbb003", "exception": "ConnectionPoolExhaustedException"}
{"timestamp": "2026-06-12T14:31:40Z", "level": "ERROR", "service": "api-gateway", "message": "ConnectionPoolExhaustedException: no connections available", "trace_id": "bbb004", "exception": "ConnectionPoolExhaustedException"}
{"timestamp": "2026-06-12T14:31:50Z", "level": "ERROR", "service": "api-gateway", "message": "ConnectionPoolExhaustedException: no connections available", "trace_id": "bbb005", "exception": "ConnectionPoolExhaustedException"}
{"timestamp": "2026-06-12T14:32:10Z", "level": "WARN", "service": "api-gateway", "message": "Query timeout after 2000ms", "trace_id": "ccc002"}
{"timestamp": "2026-06-12T14:32:30Z", "level": "INFO", "service": "api-gateway", "message": "Request processed in 2380ms", "trace_id": "ddd001"}
```

#### `data/inc-001/changes/deploys.json`
```json
{
  "incident_id": "inc-001",
  "deploys": [
    {
      "deploy_id": "846",
      "timestamp": "2026-06-12T12:00:00Z",
      "description": "Routine dependency update",
      "diff": {},
      "author": "deploy-bot"
    },
    {
      "deploy_id": "847",
      "timestamp": "2026-06-12T14:30:00Z",
      "description": "Update connection pool configuration",
      "diff": {"pool.maxSize": {"before": 50, "after": 10}},
      "author": "deploy-bot"
    },
    {
      "deploy_id": "848",
      "timestamp": "2026-06-12T14:33:00Z",
      "description": "Rollback to deploy #846",
      "diff": {"pool.maxSize": {"before": 10, "after": 50}},
      "author": "on-call-engineer"
    }
  ]
}
```

#### `data/inc-001/runbooks/api-gateway.md`
```markdown
# API Gateway Incident Response Runbook

## Overview
The API Gateway handles all inbound traffic.

## Architecture
- Upstream: Load balancer
- Downstream: Auth service, user service, data service
- Connection pool: max size 50 connections (NOTE: this may be outdated)

## Common Issues

### High Latency
1. Check P99 latency vs baseline in dashboards
2. Check connection pool usage — if >80%, scale pool size
3. Check for recent deploys in the last 30 minutes

### Recovery Procedures
- Increase pool.maxSize to 50 if pool exhaustion detected
- Rollback recent deploy if change correlation found
- Escalate to platform team if not resolved in 10 minutes
```

---

### Step 2 — Update Commander to pass `data_path`

In `agents/commander/main.py`, update `handle_alert()` to populate `data_path` on each `TriageTask`:

```python
task = TriageTask(
    task_id=str(uuid.uuid4())[:8],
    incident_id=incident_id,
    assigned_to=agent_label,
    description=f"Triage {alert.title}: {alert.description}",
    data_path=f"data/{incident_id}/",   # ← add this
    time_window="14:30-14:35",           # ← add this (or derive from alert)
)
```

---

### Step 3 — Update each agent's `analyze()` to read from files

#### Metrics Agent (`agents/metrics_agent/main.py`)

```python
import json, pathlib

def analyze(task: TriageTask, severity: Severity) -> Finding:
    data_file = pathlib.Path(task.data_path) / "metrics" / "snapshots.json"
    if data_file.exists():
        data = json.loads(data_file.read_text())
        snapshots = data.get("snapshots", [])
        # Find the peak snapshot (highest p99)
        peak = max(snapshots, key=lambda s: s.get("p99_latency_ms", 0))
        baseline_p99 = peak.get("baseline_p99_ms", 120)
        p99 = peak.get("p99_latency_ms", baseline_p99)
        pool_pct = peak.get("connection_pool_usage_pct", 0)

        is_anomaly = p99 > baseline_p99 * 3 or pool_pct > 90
        return Finding(
            finding_id=str(uuid.uuid4())[:8],
            task_id=task.task_id,
            agent="metrics-agent",
            finding_type="anomaly" if is_anomaly else "observation",
            signal="latency_spike" if p99 > baseline_p99 * 3 else "pool_saturation",
            value=f"p99={p99}ms (baseline={baseline_p99}ms), pool={pool_pct}%",
            confidence=0.9 if is_anomaly else 0.6,
            hypothesis="Connection pool exhaustion driving latency spike" if pool_pct > 90 else "Elevated latency without clear saturation",
            summary=f"Metrics analysis for {task.incident_id}: p99 {p99}ms vs baseline {baseline_p99}ms",
        )
    # Fallback to severity-based mock if no data file
    ...
```

#### Logs Agent — parse JSONL, count exceptions by type

#### Change Agent — find deploys within 10 minutes of alert, check diff keys

#### Runbook Agent — read .md file, check if documented values match actual values from other findings

---

### Step 4 — Create `inc-002` and `inc-003` scenarios

**inc-002** (Medium severity — brief latency spike, self-resolved):
- No deploy in last 48h
- P99 spike to 350ms (vs 120ms baseline) for 3 minutes
- No exception in logs, just slow queries
- Runbook matches (procedure is current)
- Expected verdict: `mitigating` (no clear root cause, no change correlation)

**inc-003** (Critical — full outage):
- Deploy 5 minutes before incident
- FATAL exceptions in logs (NullPointerException + service crash)
- CPU at 100%, memory at 95%
- Runbook is stale (procedure references deprecated endpoint)
- Expected verdict: `resolved` (high confidence deploy correlation)

---

## Acceptance Criteria

- [ ] `data/inc-001/metrics/snapshots.json` exists and contains baseline + spike data
- [ ] `data/inc-001/logs/events.jsonl` exists with 5+ ConnectionPoolExhaustedException entries
- [ ] `data/inc-001/changes/deploys.json` exists with Deploy #847 at 14:30
- [ ] `data/inc-001/runbooks/api-gateway.md` exists and references stale pool size
- [ ] Metrics Agent reads the file and produces `value="p99=2450ms (baseline=120ms), pool=98%"`
- [ ] Logs Agent reads the file and produces `value="ConnectionPoolExhaustedException×5"`
- [ ] Change Agent reads the file and produces `value="deploy #847 at 14:30, pool.maxSize 50→10"`
- [ ] Runbook Agent reads the file and flags stale pool size in its finding
- [ ] `data/inc-002/` and `data/inc-003/` exist with distinct scenarios
- [ ] All existing tests still pass (keyword fallback preserved)
