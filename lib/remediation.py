import time
from typing import List, Callable, Dict, Any
from lib.models import RemediationAction, RemediationPlan

ACTION_DETAILS = {
    "Rollback last deployment": {
        "description": "Reverting the application version to the previous stable release.",
        "simulated_command": "git-ops rollback --env prod --deploy 847",
        "severity": "CRITICAL",
        "duration": 2.5
    },
    "Check container logs for specific crash reason": {
        "description": "Querying stderr from active containers to extract crash logs.",
        "simulated_command": "kubectl logs -l app=api-gateway --tail=100 -n prod",
        "severity": "AUTO",
        "duration": 1.2
    },
    "Scale up resources": {
        "description": "Increasing the deployment replicas to distribute latency load.",
        "simulated_command": "kubectl scale deployment api-gateway --replicas=4 -n prod",
        "severity": "AUTO",
        "duration": 1.8
    },
    "Inspect underlying infrastructure health": {
        "description": "Querying cloud provider metrics for network or disk anomalies.",
        "simulated_command": "aws ec2 describe-instance-status --region us-east-1",
        "severity": "AUTO",
        "duration": 1.0
    },
    "Monitor service closely": {
        "description": "Enabling high-frequency logging and healthchecks on the service.",
        "simulated_command": "datadog-cli monitor status --id check-api-gateway",
        "severity": "AUTO",
        "duration": 1.5
    },
    "Close incident if symptoms subside": {
        "description": "Auto-closing incident ticket and resolving active pager alerts.",
        "simulated_command": "pd-cli incident resolve --id inc-001",
        "severity": "AUTO",
        "duration": 0.8
    }
}

def map_action_string_to_model(action_str: str) -> RemediationAction:
    for key, details in ACTION_DETAILS.items():
        if key.lower() in action_str.lower():
            return RemediationAction(
                name=key,
                description=details["description"],
                simulated_command=details["simulated_command"],
                severity=details["severity"],
                duration=details["duration"]
            )
    # Default fallback if not matched
    return RemediationAction(
        name=action_str,
        description=f"Executing recommended step: {action_str}",
        simulated_command=f"run-mitigation --task '{action_str}'",
        severity="AUTO",
        duration=1.0
    )

class RemediationEngine:
    def __init__(self, plan: RemediationPlan):
        self.plan = plan

    @classmethod
    def from_recommendations(cls, incident_id: str, recommendations: List[str]) -> "RemediationEngine":
        actions = [map_action_string_to_model(rec) for rec in recommendations]
        plan = RemediationPlan(incident_id=incident_id, actions=actions)
        return cls(plan)

    def execute(self, progress_callback: Callable[[RemediationAction, str, float], None] = None):
        """
        Simulates the execution of the remediation plan.
        progress_callback: (action, status, progress_percent) -> None
        """
        self.plan.status = "RUNNING"
        start_time = time.time()
        
        for action in self.plan.actions:
            action.status = "RUNNING"
            action.started_at = time.time()
            if progress_callback:
                progress_callback(action, "START", 0.0)

            # Simulate duration with steps
            steps = int(action.duration * 10)  # 10 steps per second
            step_duration = action.duration / max(steps, 1)
            
            for step in range(1, steps + 1):
                time.sleep(step_duration)
                progress = step / max(steps, 1)
                if progress_callback:
                    progress_callback(action, "PROGRESS", progress)

            action.status = "COMPLETED"
            action.completed_at = time.time()
            if progress_callback:
                progress_callback(action, "COMPLETED", 1.0)

        end_time = time.time()
        self.plan.total_mttr = round(end_time - start_time, 2)
        self.plan.status = "COMPLETED"
