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

## Phase 4 — Evidence + Scoring + Artifact System ✅
- `lib/evidence.py`: in-memory `EvidenceStore` — every finding, deliberation message,
  and verdict is recorded as `Evidence` (id, incident_id, agent, type, content, timestamp)
- `lib/scorer.py`: `compute_confidence()` — weighted average of agent confidences
  (Metrics 0.25, Logs 0.25, Change 0.25, Runbook 0.15, Deliberation 0.10) with
  AGREE/CHALLENGE/CONNECT/SURFACE bonuses/penalties; `gate()` maps confidence to
  resolved (>=0.80) / mitigating (>=0.50) / escalated (<0.50)
- `lib/artifact_generator.py`: renders `draft_postmortem` (markdown) and `status_page`
  text from root cause, severity, remediation, and the evidence trail
- Commander's `generate_verdict()` now publishes a full `CommanderVerdict`: status,
  root_cause, severity (SEV-1/2/3), confidence, remediation, draft_postmortem,
  status_page, evidence_ids, deliberation_summary
- Files: `lib/evidence.py`, `lib/scorer.py`, `lib/artifact_generator.py`,
  `agents/commander/main.py`

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
