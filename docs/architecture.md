# Architecture

## Agent Roster

| Agent | Framework | Data Source | Core Job | Deliberation Role |
|-------|-----------|-------------|----------|-------------------|
| **Incident Commander** | LangGraph | All findings | Orchestrate, score, gate, publish verdict | Synthesis |
| **Metrics Agent** | CrewAI | `data/metrics/` | Latency, error rate, saturation analysis | AGREE, CHALLENGE |
| **Logs & Traces Agent** | Anthropic SDK | `data/logs/` | Stack traces, error frequency, log correlation | CHALLENGE, SURFACE |
| **Change Agent** | Pydantic AI | `data/changes/` | Deploy correlation, config diffs, feature flags | CONNECT, AGREE |
| **Runbook Agent** | Claude SDK | `data/runbooks/` | Staleness detection, procedure drift | SURFACE |

---

## Band Channels

| Channel | Purpose | Publishers | Subscribers |
|---------|---------|------------|-------------|
| `#incident-events` | Incoming alerts | Alert system | Commander |
| `#agent-registry` | Agent heartbeat/discovery | All agents | All agents |
| `#triage-tasks` | Task assignments | Commander | Metrics, Logs, Change, Runbook |
| `#triage-findings` | Triage results | All 4 specialists | Commander + all agents |
| `#deliberation` | Council deliberation (AGREE/CHALLENGE/etc.) | All agents | All agents + human |
| `#commander-verdict` | Final verdict + artifact | Commander | All agents + human |
| `#errors` | Error notifications | Any agent | Commander, human |

---

## Message Envelope Schema

All Band messages use this wrapper:

```json
{
  "message_id": "uuid-short",
  "channel": "triage-tasks",
  "sender": "commander",
  "payload": { },
  "timestamp": "ISO8601"
}
```

---

## Pydantic Models (`lib/models.py`)

```python
class Severity(IntEnum):     LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4
class Evidence               id, incident_id, agent, type, content, timestamp
class IncidentAlert          id, title, description, severity
class TriageTask             task_id, incident_id, assigned_to, description, data_path, time_window
class Finding                finding_id, task_id, agent, finding_type, signal, value,
                             confidence, hypothesis, summary, evidence[], supporting_data{}
class DeliberationMessage    message_id, sender, content
class CommanderVerdict       incident_id, status, verdict, root_cause, severity, confidence,
                             remediation[], draft_postmortem, status_page,
                             evidence_ids[], deliberation_summary{}, timestamp
```

---

## Evidence IDs

Format: `EVD-{PREFIX}-{uuid_short}`

| Agent | Prefix |
|-------|--------|
| commander | CM |
| metrics-agent | MT |
| logs-agent | LG |
| change-agent | CH |
| runbook-agent | RB |

---

## Confidence Scoring (`lib/scorer.py`)

**Base score**: weighted average of agent confidences

| Agent | Weight |
|-------|--------|
| metrics-agent | 0.25 |
| logs-agent | 0.25 |
| change-agent | 0.25 |
| runbook-agent | 0.15 |
| deliberation | 0.10 |

**Deliberation adjustments**:
- Resolved CHALLENGE (CHALLENGE + AGREE/CONNECT in same session): `+0.10`
- Unresolved CHALLENGE: `-0.10`
- Each CONNECT: `+0.05`
- Each AGREE: `+0.02`
- SURFACE without follow-up CONNECT: `-0.05`

**Gate thresholds**:
- `≥ 0.80` → `resolved`
- `0.50–0.79` → `mitigating`
- `< 0.50` → `escalated`

---

## Directory Structure

```
The-war-room/
├── agents/
│   ├── commander/        main.py — handle_alert(), handle_finding(), generate_verdict()
│   ├── metrics_agent/    main.py — analyze(), handle_task()
│   ├── logs_agent/       main.py — analyze(), handle_task()
│   ├── change_agent/     main.py — analyze(), handle_task()
│   └── runbook_agent/    main.py — analyze(), handle_task()
├── lib/
│   ├── models.py         All Pydantic schemas
│   ├── band_client.py    BandClientWrapper (mock pub/sub/poll)
│   ├── evidence.py       EvidenceStore (in-memory)
│   ├── scorer.py         compute_confidence(), gate()
│   └── artifact_generator.py  generate_postmortem(), generate_status_page()
├── data/
│   ├── inc-001/
│   │   └── alert.json    API Gateway latency spike alert
│   ├── metrics/          (Phase 5: snapshots.json per incident)
│   ├── logs/             (Phase 5: events.jsonl per incident)
│   ├── changes/          (Phase 5: deploys.json per incident)
│   └── runbooks/         (Phase 5: service runbook .md files)
├── band/
│   ├── agents.yaml       5 agent registrations
│   └── channels.yaml     7 channel definitions
├── tests/                pytest test files (one per agent + lib module)
├── demo/
│   ├── demo-script.md
│   └── run_demo.py
├── ui/                   dashboard.html + CSS tokens
├── phases.md             Build phase tracker
└── pyproject.toml
```
