# Demo Script & Presentation Guide

## 90-Second Demo Script

### Phase 0: Setup (0–10s)
**Visual**: Band dashboard with 5 registered agents visible in `#war-room`

> *"A production alert just fired. Five specialized agents automatically convene in the War Room."*

---

### Phase 1: Alert + Parallel Triage (10–30s)

```
System → #incident-events:
  INCIDENT: API Gateway — P99 latency spike to 2450ms (SEV-2)

@Commander → #triage-tasks:
  @metrics-agent @logs-agent @change-agent @runbook-agent — triage inc-001

[Within 5 seconds, all 4 post to #triage-findings:]
@Metrics:  "P99: 120ms → 2450ms, pool usage 98%"
@Logs:     "ConnectionPoolExhaustedException × 5 at 14:31"
@Change:   "Deploy #847 at 14:30 — pool.maxSize changed 50→10"
@Runbook:  "API Gateway runbook section still references pool size 50 — stale"
```

> *"Four agents, four different data sources, four findings — in parallel."*

---

### Phase 2: Deliberation (30–55s) ← THE KEY MOMENT

```
@Logs:    "@Metrics CHALLENGE — no slow queries in logs. It's pool exhaustion, not DB."
@Metrics: "@Logs AGREE — pool at 98% confirms connection exhaustion."
@Change:  "@Metrics @Logs CONNECT — Deploy #847 at 14:30 reduced pool max from 50 to 10."
@Runbook: "SURFACE — runbook for api-gateway still says pool size 50. Procedure is stale."

[Human types in chat]:
  "@ChangeAgent check the 14:31 deploy"

@Change:  "Deploy #847: pool.maxSize changed 50→10 by config update. Rollback to #846 restores to 50."
```

> *"Three agents, different data, genuinely deliberating. A CHALLENGE, an AGREE, a CONNECT, a SURFACE — and a human asking a question in real time. This is the innovation."*

---

### Phase 3: Commander Verdict (55–75s)

```
@Commander → #commander-verdict:
  Status:     RESOLVED (confidence 0.87)
  Root Cause: Deploy #847 reduced connection pool from 50 to 10
  Severity:   SEV-2
  Remediation:
    1. Rollback deploy #847
    2. Increase pool.maxSize to 50
    3. Add connection pool monitoring alert

  Draft Postmortem: [markdown artifact]
  Status Page: "Resolved: API Gateway latency spike — root cause identified, rolling back deploy #847"
```

> *"The CHALLENGE was resolved by CONNECT. Confidence: 87%. Verdict: resolved."*

---

### Phase 4: Close (75–90s)

**Visual**: Full Band transcript — all messages visible
**Visual**: Evidence trail — EVD-MT-xxx, EVD-LG-xxx, EVD-CH-xxx, EVD-RB-xxx
**Visual**: Artifact — postmortem markdown + status page text

> *"The full transcript is the permanent record. Every finding, every challenge, every connection — auditable and replayable. This is what happens when agents collaborate through Band."*

---

## Deliberation Protocol Reference

| Verb | Who uses it | Effect |
|------|-------------|--------|
| `AGREE` | Any agent confirming another's finding | Confidence +0.02 to both |
| `CHALLENGE` | Any agent disputing a finding | Confidence -0.10; triggers resolution round |
| `CONNECT` | Agent linking their finding to another's | Confidence +0.05 to both; resolves a CHALLENGE |
| `SURFACE` | Agent with a new finding triggered by another's | New finding gets novelty penalty (×0.8 confidence) |

**Rule**: The demo MUST contain at least 1 CHALLENGE. Without it, the system looks like scripted theater.

---

## Slide Deck Outline (7 Slides)

### Slide 1: Title + Problem
- Title: "The War Room — AI Incident Response"
- Problem: Production outages cost $300K–$1M/hr. Root cause analysis is a manual bottleneck.
- Hook: "What if your on-call team was already awake — and had already read everything?"

### Slide 2: The War Room Concept
- Band chat room = the war room
- "Remove Band → system has no communication layer"
- Alert → agents convene → deliberate → verdict

### Slide 3: 5 Agents + Their Data Sources
- Agent table (name, framework, data source, role)
- Key point: each reads different data → collaboration is genuine, not theater

### Slide 4: The Deliberation Protocol
- AGREE / CHALLENGE / CONNECT / SURFACE diagram
- "This is not a pipeline. Agents read each other's findings and respond."
- Highlight: CHALLENGE is the proof of genuine multi-agent reasoning

### Slide 5: Live Demo (90s video)
- Full War Room in action

### Slide 6: Why Band?
- "The chat room IS the war room"
- @mention routing = context isolation per agent
- Full transcript = permanent audit trail
- Human intervention = natural (just type in the chat)

### Slide 7: Business Value + Next Steps
- Current: mock data, rule-based analysis
- Production path: plug in Datadog, Splunk, PagerDuty
- Value: faster MTTR, automatic postmortems, stale runbook detection
