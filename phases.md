# The War Room — 6 Phases

## Phase 1 — Commander Triage ✅
- Alert handler generates `incident_id`
- Fans out `TriageTask` to all agents via `triage-tasks` channel
- Files: `agents/commander/main.py`

## Phase 2 — Analysis Agents ✅
- Metrics Agent: severity-based anomaly/observation detection
- Logs Agent: log pattern scanning (error, timeout, crash)
- Change Agent: deploy/release/rollback correlation
- Runbook Agent: runbook matching + recommended actions
- All publish to `triage-findings`, low-sev goes to `deliberation`
- Files: `agents/{metrics,logs,change,runbook}_agent/main.py`

## Phase 3 — Commander Verdict
- Commander listens to `triage-findings`
- Collects all agent findings for an incident
- Publishes a verdict to `commander-verdict` channel
- Deliberation channel becomes read-write: agents discuss before verdict

## Phase 4 — Multi-Agent Coordination
- Wire LangGraph/CrewAI flows (already in `pyproject.toml`)
- Agent registry for discovery
- Agents cross-reference findings (e.g. "logs saw 5xx + change saw deploy = root cause")
- Escalation paths between agents

## Phase 5 — Real Data Pipeline
- Replace keyword-scanning with real data sources
- Parse CSV logs, metrics APIs, deployment webhooks
- Realistic demo scenarios (3+ incident scripts)
- `data/` directory with proper fixtures

## Phase 6 — Dashboard & Presentation
- Streamlit or React dashboard
- Real-time: alert comes in → agents work → verdict appears
- Architecture diagram
- Demo script + slides
- Video recording
