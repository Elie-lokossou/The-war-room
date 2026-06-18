# "The War Room" Simulation Walkthrough & Demo Guide

This guide describes how to run and interpret the automated CLI simulation for **The War Room**—our multi-agent, collaborative Incident Response platform. 

The demo script replicates the entire event-driven architecture of the platform, demonstrating how multiple AI agent frameworks collaborate to triage an incident and produce a coordinated resolution verdict.

---

## Prerequisite Setup

Before running the simulation, make sure your Python dependencies are installed. You can install the requirements defined in `pyproject.toml` (this workspace relies on standard libraries and Pydantic):

```bash
pip install pydantic
```

*(Note: In a production setup with live APIs, you would install the full `band-sdk` suite via `pip install "band-sdk[langgraph,crewai,anthropic,pydantic-ai,claude_sdk]"`).*

---

## Running the CLI Simulation

To execute the automated incident triage simulation, run the following command from the project root:

```bash
python demo/run_demo.py
```

---

## Detailed Demo Walkthrough

When you run the simulation, it steps through **5 key stages** representing a real-world SRE Incident Command protocol:

### Stage 1: Incident Commander Triage Allocation
- **What happens:** An incoming incident alert (loaded from [alert.json](file:///home/elie/Downloads/Hack/The-war-room/data/inc-001/alert.json)) triggers the system. The **Incident Commander** registers the alert and spawns 4 targeted triage tasks on the `triage-tasks` channel, assigning them to their respective specialized agents.
- **Console Output:** Shows the alert metadata (Severity: HIGH, Title, Description) and the 4 published tasks fanning out.

### Stage 2: Multi-Agent Parallel Domain Triage
- **What happens:** The specialized agents poll the `triage-tasks` channel. Each agent boots up and analyzes the system state within its respective domain:
  - **Metrics Agent** (CrewAI representation) inspects metrics anomalies.
  - **Logs Agent** (Anthropic SDK representation) parses system exceptions.
  - **Change Agent** (Pydantic AI representation) audits deployment pipelines.
  - **Runbook Agent** (Claude SDK representation) looks up mitigation guides.
- **Console Output:** Informational logs indicating telemetry parsing and log tracking.

### Stage 3: Triage Findings Reported
- **What happens:** Each agent generates a structured `Finding` model (featuring finding type, signals, confidence scores, and hypotheses) and publishes it to the `triage-findings` channel.
- **Console Output:** Shows color-coded, detailed breakdowns of findings for each agent. For example, the Metrics Agent reports an `anomaly` with `0.90` confidence, while the Logs Agent alerts on `log_anomaly`.

### Stage 4: Incident War Room Deliberation Chat
- **What happens:** For low/medium-severity incidents, the agents post status summaries and deliberate asynchronously in the `deliberation` chat room channel.
- **Console Output:** If the severity permits, chat logs from the agents are displayed here. (For high-severity alerts like the Latency Spike, the Commander directly intervenes).

### Stage 5: Incident Verdict & Resolution Coordination
- **What happens:** The **Incident Commander** synthesizes all triage findings and the runbook recommendations to issue a final verdict and a checklist of remediation tasks.
- **Console Output:** Displays the Commander's verdict summary and a step-by-step checklist (e.g., scale DB replicas, rollback configurations, notify SRE on-call).
