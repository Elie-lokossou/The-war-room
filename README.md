# 🚨 The War Room: AI-Driven Incident Response Platform

> **Foundry System Implementation**
> *Automating cloud infrastructure triage and resolution coordination using cooperative AI Agent Swarms.*

---

## 📖 Project Overview

**The War Room** is a multi-agent Incident Response platform that automates the critical minutes following a service outage. Built on the **Band SDK** (the "Foundry"), it coordinates specialized AI agents that analyze logs, metrics, and changes in parallel to find the root cause.

Traditional on-call engineering is reactive and manual. **The War Room** is proactive and collaborative, simulating a synchronized "War Room" where agents exchange findings, deliberate on causes, and coordinate a mitigation plan in real-time.

### 🧠 How it Works: The Foundry Logic
The system follows a strict event-driven lifecycle:
1.  **Ingestion**: Alerts from Datadog/PagerDuty are received.
2.  **Triage Allocation**: The **Incident Commander** fans out specific tasks to domain experts.
3.  **Domain Analysis**: Specialized agents (Metrics, Logs, Change, Runbook) perform deep-dives.
4.  **Cross-Domain Correlation**: The Commander synthesizes independent findings.
    *   *Example*: `Logs (5xx Errors)` + `Change (Recent Deploy)` = `CRITICAL: Rollback Recommended`.
5.  **Automated Verdict**: A final resolution plan is published with recommended actions.

---

## 🛠️ Architecture & Tech Stack

| Component | Role | Tech / Framework |
| :--- | :--- | :--- |
| **Band SDK** | The Foundry / Message Bus | Python SDK |
| **Incident Commander** | Orchestrator & Synthesizer | LangGraph / Logic-based |
| **Metrics Agent** | Telemetry Analyst | CrewAI |
| **Logs Agent** | Exception & Trace Audit | Anthropic SDK |
| **Change Agent** | CI/CD & Deploy Audit | Pydantic AI |
| **Runbook Agent** | Playbook Matcher | Claude SDK |

---

## 📁 Repository Structure

```bash
├── agents/             # Domain-specific AI agents
│   ├── commander/      # Orchestrates triage and synthesizes verdicts
│   ├── metrics_agent/  # Telemetry and anomaly detection
│   ├── logs_agent/     # Log pattern and error scanner
│   ├── change_agent/   # Deployment and config correlation
│   └── runbook_agent/  # Playbook lookup and recommendations
├── band/               # Foundry configuration (registry & channels)
├── lib/                # Shared Pydantic models and Band client wrapper
├── tests/              # Comprehensive test suite (Logic & Integration)
├── demo/               # Interactive console simulation
└── .foundary/          # Foundry Design System (Slate UI Kit)
```

---

## 🚀 Getting Started

### 1. Installation
The project uses a Python virtual environment to manage dependencies like `pydantic` and `pytest`.

```bash
python3 -m venv venv
source venv/bin/activate
pip install pydantic pytest
```

### 2. Running the Simulation
Experience the full automated triage flow in your console:
```bash
python3 The-war-room/demo/run_demo.py
```

### 3. Testing
Validate the correlation logic and agent behaviors:
```bash
python3 -m pytest The-war-room/tests
```

---

## 🎯 Current Status: Phase 3 Complete
- [x] **Phase 1: Triage Allocation** (Fan-out tasks to agents).
- [x] **Phase 2: Analysis Agents** (Metrics, Logs, Change, Runbook).
- [x] **Phase 3: Automated Verdict** (Cross-domain correlation & resolution).
- [ ] **Phase 4: Multi-Agent Coordination** (Inter-agent chat & deliberation).
- [ ] **Phase 6: Web Dashboard** (Real-time UI using Slate Design System).
