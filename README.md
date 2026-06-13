# The War Room

The War Room is an AI-driven, multi-agent Incident Response platform demonstrating automated triage and resolution coordination using various AI agent frameworks.

## Directory Structure
- `agents/`: Contains individualized AI agents.
- `lib/`: Shared Pydantic models, wrappers, and evidence handlers.
- `data/`: Placeholder logic for logs, metrics, changes, and runbook definitions.
- `band/`: Contains agent schema bindings and channel setups.
- `demo/`: Scripts for presenting the workflow.

## Progress (Phase 0)
- [x] Initial directory scaffolding & project setup
- [x] Configured dependency mapping via `pyproject.toml`
- [x] Defined unified message schemas via Pydantic model configurations (`IncidentAlert`, `TriageTask`, `Finding`, etc.)
- [x] Implemented preliminary logic for Evidence handling & ID generators
- [x] Abstracted Band SDK communication wrapper (`BandClientWrapper`) with mocked outputs
- [x] Registered 7 crucial response channels (`band/channels.yaml`)
- [x] Configured registration specs for 5 core agents (`band/agents.yaml`)

## Constraints Established
1. Connecting with actual APIs is deferred until later phases.
2. Generating fake analytics data is deferred until Phase 5.
3. Writing tests is pending Phase 5.
