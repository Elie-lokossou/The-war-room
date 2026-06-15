# The War Room — Project Overview

> **Hackathon**: Band of Agents (June 12–19, 2026) — lablab.ai
> **Submission deadline**: June 19, 2026
> **Prize pool**: $10,000+

---

## What We're Building

A multi-agent **Incident Response War Room** where 5 specialized agents convene in a Band chatroom when a production alert fires. Each agent reads a **different data source** — dashboards, logs, deploys, runbooks — and deliberates together to find root cause and produce a remediation artifact.

**Core value**: Band chat room IS the war room. Remove Band → the system has no communication layer. All deliberation, task handoffs, @mention routing, and artifact publishing happen through Band.

---

## Why This Wins

| Problem with typical submissions | Our solution |
|----------------------------------|--------------|
| Band is decorative (final notification only) | Band IS the collaboration layer — every agent interaction goes through it |
| Single-agent systems fake collaboration | Each agent reads **different data** → collaboration is genuine |
| Demos are boring (agents always agree) | Built-in **CHALLENGE + resolution** — conflict is scripted into the demo |
| Code-review agents dominate → saturated | Incident response is **uncontested** at this hackathon |

---

## High-Level Flow

```
ALERT FIRES
    │
    ▼
Incident Commander
    │  generates incident_id, fans out tasks via #triage-tasks
    ├──► @metrics-agent   → reads metrics JSON → posts finding to #triage-findings
    ├──► @logs-agent      → reads log files   → posts finding to #triage-findings
    ├──► @change-agent    → reads deploy history → posts finding to #triage-findings
    └──► @runbook-agent   → reads runbook docs  → posts finding to #triage-findings
             │
             ▼
    Council Deliberation (#deliberation channel)
    Agents use AGREE / CHALLENGE / CONNECT / SURFACE verbs
    Human on-call can @mention agents in real time
             │
             ▼
    Commander collects all findings + deliberation
    Computes confidence score → gates verdict
    Publishes CommanderVerdict to #commander-verdict
    (includes root_cause, severity, remediation, draft postmortem, status page)
```

---

## Demo Scenario (inc-001)

**Alert**: API Gateway P99 latency spiked to 2450ms (baseline 120ms)

**Root cause**: Deploy #847 accidentally reduced connection pool from 50 → 10

**The key deliberation moment**:
- Logs Agent: `@Metrics CHALLENGE — no slow queries in logs. It's pool exhaustion, not DB.`
- Metrics Agent: `@Logs AGREE — pool usage at 98% confirms.`
- Change Agent: `@Metrics @Logs CONNECT — Deploy #847 at 14:30 reduced pool 50→10.`
- Runbook Agent: `SURFACE — runbook still says pool size 50. It's stale.`
- Human: `@ChangeAgent check the 14:31 deploy`
- Change Agent: `Deploy #847: pool.maxSize changed 50→10 by config update.`

**Commander verdict**: `RESOLVED` (confidence 0.87) — rollback #847, increase pool to 50, add monitoring.

---

## Judging Criteria

| Criterion | How we satisfy it |
|-----------|-------------------|
| **Band usage depth** | Chat room is the war room; all task handoffs + deliberation + artifacts go through Band |
| **Clarity of demo** | 90-second script with phase transitions; transcript IS the demo |
| **Project quality** | Real enterprise problem ($300K–$1M/hr outage cost); immediately useful artifact |
