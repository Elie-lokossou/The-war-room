import sys
import os
import json
import time

# Add the project root to sys.path so we can import lib and agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, TriageTask, Finding, Severity, CommanderVerdict

# Import agent modules
import agents.commander.main as commander_agent
import agents.metrics_agent.main as metrics_agent
import agents.logs_agent.main as logs_agent
import agents.change_agent.main as change_agent
import agents.runbook_agent.main as runbook_agent

# Console coloring utilities
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"

def print_header(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{MAGENTA} {title} {RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def print_agent_log(agent_name, message, color=GREEN):
    print(f"{BOLD}{color}[{agent_name}]{RESET} {message}")

def main():
    # 1. Initialize Shared Band Client
    shared_band = BandClientWrapper()

    # 2. Inject shared band client into all agents
    commander_agent.band = shared_band
    metrics_agent.band = shared_band
    logs_agent.band = shared_band
    change_agent.band = shared_band
    runbook_agent.band = shared_band

    # 3. Subscribe agent handlers to the shared channels
    shared_band.subscribe("incident-events", commander_agent.handle_alert)
    shared_band.subscribe("triage-tasks", metrics_agent.handle_task)
    shared_band.subscribe("triage-tasks", logs_agent.handle_task)
    shared_band.subscribe("triage-tasks", change_agent.handle_task)
    shared_band.subscribe("triage-tasks", runbook_agent.handle_task)
    shared_band.subscribe("triage-findings", commander_agent.handle_finding)

    print_header("THE WAR ROOM - MULTI-AGENT INCIDENT RESPONSE SIMULATION")
    
    # 4. Load Incident Alert
    alert_path = os.path.join(os.path.dirname(__file__), "..", "data", "inc-001", "alert.json")
    if not os.path.exists(alert_path):
        print(f"{RED}Error: Alert file not found at {alert_path}{RESET}")
        return

    with open(alert_path, "r") as f:
        alert_data = json.load(f)
    
    alert = IncidentAlert(**alert_data)
    
    print(f"{BOLD}Incident Alert Detected:{RESET}")
    print(f"  - {BOLD}ID:{RESET} {alert.id}")
    print(f"  - {BOLD}Title:{RESET} {YELLOW}{alert.title}{RESET}")
    print(f"  - {BOLD}Description:{RESET} {alert.description}")
    print(f"  - {BOLD}Severity:{RESET} {RED if alert.severity >= Severity.HIGH else YELLOW}{alert.severity.name} (Value: {alert.severity.value}){RESET}")
    time.sleep(1)

    # 5. Trigger the Commander
    print_header("STAGE 1: INCIDENT COMMANDER TRIAGE ALLOCATION")
    print_agent_log("Commander", "Received alert. Creating Incident Space & assigning tasks...", BLUE)
    
    # Publish incident alert
    shared_band.publish("incident-events", alert.model_dump(), "alert-system")
    
    # Poll incident events so the commander receives the alert and fans out tasks
    shared_band.poll("incident-events")
    time.sleep(1)

    # Print out assignments
    triage_tasks_queue = shared_band.message_queue.get("triage-tasks", [])
    print(f"\n{BOLD}Commander Published Triage Tasks ({len(triage_tasks_queue)}):{RESET}")
    for idx, envelope in enumerate(triage_tasks_queue):
        payload = envelope["payload"]
        print(f"  [{idx + 1}] Assigned to: {GREEN}{payload['assigned_to']}{RESET}")
        print(f"      Description: {payload['description']}")
    time.sleep(1.5)

    # 6. Execute Triage Agents
    print_header("STAGE 2: MULTI-AGENT PARALLEL DOMAIN TRIAGE")
    
    # Poll triage-tasks so each agent processes all tasks
    while shared_band.message_queue.get("triage-tasks"):
        shared_band.poll("triage-tasks")
    
    time.sleep(1)

    # 7. Collect Findings
    findings_queue = shared_band.message_queue.get("triage-findings", [])
    deliberation_queue = shared_band.message_queue.get("deliberation", [])

    print_agent_log("Metrics Agent", "Analyzing CPU, Memory & Latency telemetry...", GREEN)
    print_agent_log("Logs Agent", "Searching through application exceptions and tracing IDs...", YELLOW)
    print_agent_log("Change Agent", "Checking deployment pipelines and configurations...", CYAN)
    print_agent_log("Runbook Agent", "Querying matching runbooks and mitigation runsheets...", MAGENTA)
    time.sleep(1.5)

    print_header("STAGE 3: TRIAGE FINDINGS REPORTED")
    
    # Let's deduplicate or group findings by agent to display them clearly
    findings_by_agent = {}
    for envelope in findings_queue:
        payload = envelope["payload"]
        agent = payload["agent"]
        if agent not in findings_by_agent:
            findings_by_agent[agent] = Finding(**payload)

    for agent, finding in findings_by_agent.items():
        color = GREEN if "metrics" in agent else YELLOW if "logs" in agent else CYAN if "change" in agent else MAGENTA
        print(f"\n{BOLD}{color}>>> {agent.upper()} Finding Details:{RESET}")
        print(f"  - {BOLD}Finding ID:{RESET} {finding.finding_id}")
        print(f"  - {BOLD}Type:{RESET} {finding.finding_type}")
        print(f"  - {BOLD}Signal:{RESET} {finding.signal}")
        print(f"  - {BOLD}Value:{RESET} {finding.value}")
        print(f"  - {BOLD}Confidence:{RESET} {color}{finding.confidence:.2f}{RESET}")
        print(f"  - {BOLD}Hypothesis:{RESET} {finding.hypothesis}")
        print(f"  - {BOLD}Summary:{RESET} {finding.summary}")
        if finding.supporting_data:
            print(f"  - {BOLD}Supporting Data:{RESET} {finding.supporting_data}")
        time.sleep(1)

    # 8. Show Deliberations (if any)
    if deliberation_queue:
        print_header("STAGE 4: INCIDENT WAR ROOM DELIBERATION CHAT")
        shown_messages = set()
        for envelope in deliberation_queue:
            payload = envelope["payload"]
            sender = payload["sender"]
            content = payload["content"]
            msg_key = f"{sender}:{content}"
            if msg_key not in shown_messages:
                shown_messages.add(msg_key)
                color = GREEN if "metrics" in sender else YELLOW if "logs" in sender else CYAN if "change" in sender else MAGENTA
                print(f"[CHAT] {BOLD}{color}{sender}:{RESET} \"{content}\"")
                time.sleep(1)
    else:
        print(f"\n{BOLD}{YELLOW}No deliberations reported (Incident severity requires direct Commander verdict).{RESET}\n")

    # 9. Formulate Verdict
    print_header("STAGE 5: INCIDENT VERDICT & RESOLUTION COORDINATION")
    
    print_agent_log("Commander", "Synthesizing triage reports and runbook recommendations...", BLUE)
    
    # Poll triage-findings so the commander processes them and generates a verdict
    while shared_band.message_queue.get("triage-findings"):
        shared_band.poll("triage-findings")
        
    time.sleep(1.5)

    verdict_queue = shared_band.message_queue.get("commander-verdict", [])
    if verdict_queue:
        payload = verdict_queue[0]["payload"]
        verdict_desc = payload["verdict"]
        actions = payload["remediation"]

        print(f"\n{BOLD}{GREEN}[VERDICT] Commander Verdict Formulated:{RESET}")
        print(f"  - {BOLD}Incident ID:{RESET} {payload['incident_id']}")
        print(f"  - {BOLD}Status:{RESET} {YELLOW}{payload['status'].upper()}{RESET} (confidence={payload['confidence']:.2f})")
        print(f"  - {BOLD}Severity:{RESET} {payload['severity']}")
        print(f"  - {BOLD}Verdict:{RESET} {YELLOW}{verdict_desc}{RESET}")
        print(f"  - {BOLD}Root Cause:{RESET} {payload['root_cause']}")
        print(f"  - {BOLD}Actions Recommended:{RESET}")
        for idx, act in enumerate(actions):
            print(f"    {idx+1}. {act}")
        print(f"  - {BOLD}Evidence IDs:{RESET} {', '.join(payload['evidence_ids'])}")
        print(f"  - {BOLD}Deliberation Summary:{RESET} {payload['deliberation_summary']}")

        print_header("STAGE 6: GENERATED ARTIFACTS")
        print(f"{BOLD}{CYAN}-- Status Page Update --{RESET}")
        print(payload["status_page"])
        print(f"\n{BOLD}{CYAN}-- Draft Postmortem --{RESET}")
        print(payload["draft_postmortem"])

        print_header("STAGE 7: HUMAN-IN-THE-LOOP REMEDIATION")
        from lib.remediation import RemediationEngine
        engine = RemediationEngine.from_recommendations(payload["incident_id"], actions)

        print(f"{BOLD}Proposed Remediation Plan:{RESET}")
        for idx, act in enumerate(engine.plan.actions):
            sev_color = RED if act.severity == "CRITICAL" else GREEN
            print(f"  [{idx+1}] {sev_color}[{act.severity}]{RESET} {BOLD}{act.name}{RESET} - {act.description}")
            print(f"      {CYAN}Command:{RESET} `{act.simulated_command}` ({act.duration}s)")
        print()

        choice = input(f"{BOLD}Do you want to execute this remediation plan? (y/n): {RESET}").strip().lower()
        if choice == 'y':
            print(f"\n{BOLD}{YELLOW}Executing remediation actions...{RESET}")

            def cli_progress_callback(action, event_type, progress):
                if event_type == "START":
                    sev_color = RED if action.severity == "CRITICAL" else GREEN
                    sys.stdout.write(f"  {sev_color}[{action.severity}]{RESET} {action.name} ... ")
                    sys.stdout.flush()
                elif event_type == "PROGRESS":
                    sys.stdout.write(".")
                    sys.stdout.flush()
                elif event_type == "COMPLETED":
                    sys.stdout.write(f" {GREEN}✅ Done{RESET}\n")
                    sys.stdout.flush()

            engine.execute(progress_callback=cli_progress_callback)
            print(f"\n{BOLD}{GREEN}✅ INCIDENT RESOLVED — MTTR: {engine.plan.total_mttr}s — Status: RESOLVED{RESET}")
        else:
            print(f"\n{BOLD}{RED}Human declined — incident queued for manual resolution{RESET}")

        # --- STAGE 8: AUTO-POSTMORTEM GENERATION & GIT-OPS COMMIT ---
        print_header("STAGE 8: AUTO-POSTMORTEM GENERATION & GIT-OPS COMMIT")
        print(f"{BOLD}📝 Drafting postmortem...{RESET}")
        time.sleep(1)

        from lib.postmortem_generator import generate_postmortem
        from lib.git_ops import commit_postmortem, get_commit_url

        # Build Findings list and Deliberation log
        findings_objs = []
        for env in findings_queue:
            findings_objs.append(Finding(**env["payload"]))

        delib_msgs = []
        for env in deliberation_queue:
            delib_msgs.append(env["payload"])

        postmortem_md = generate_postmortem(
            verdict=CommanderVerdict(**payload),
            findings=findings_objs,
            deliberation_log=delib_msgs,
            total_mttr=engine.plan.total_mttr if choice == 'y' else 0.0
        )

        # Show sections of the postmortem
        print(f"\n{BOLD}{CYAN}Previewing Postmortem Sections:{RESET}")
        lines = postmortem_md.split("\n")
        # Print first 18 lines or key sections
        for line in lines[:18]:
            print(f"  {line}")
        print(f"  {BOLD}... [truncated for CLI preview] ...{RESET}\n")

        # Commit to Git
        print(f"{BOLD}📤 Committing to git...{RESET}")
        success, commit_hash = commit_postmortem(payload["incident_id"], postmortem_md)
        if success:
            if commit_hash:
                print(f"{GREEN}✅ Postmortem successfully committed to Git [hash: {commit_hash}]{RESET}")
                url = get_commit_url(commit_hash)
                print(f"🔗 Commit URL: {UNDERLINE}{BLUE}{url}{RESET}")
            else:
                print(f"{YELLOW}⚠️ Git not available or not a repo. Saved postmortem to file system only.{RESET}")
        else:
            print(f"{RED}❌ Failed to save or commit postmortem.{RESET}")
    else:
        print(f"\n{BOLD}{RED}No verdict published by the Commander.{RESET}")

    print(f"\n{BOLD}{GREEN}=== SIMULATION COMPLETE ==={RESET}\n")

if __name__ == "__main__":
    main()
