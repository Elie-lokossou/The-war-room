import pytest
from lib.remediation import RemediationEngine, map_action_string_to_model
from lib.models import RemediationPlan, RemediationAction

def test_map_action_string_known():
    action = map_action_string_to_model("Rollback last deployment")
    assert action.name == "Rollback last deployment"
    assert action.severity == "CRITICAL"
    assert action.duration == 2.5
    assert "rollback" in action.simulated_command

def test_map_action_string_fallback():
    action = map_action_string_to_model("Nonexistent action string")
    assert action.name == "Nonexistent action string"
    assert action.severity == "AUTO"
    assert action.duration == 1.0
    assert "run-mitigation" in action.simulated_command

def test_remediation_engine_execution():
    recommendations = ["Rollback last deployment", "Scale up resources"]
    engine = RemediationEngine.from_recommendations("inc-test", recommendations)
    
    assert len(engine.plan.actions) == 2
    assert engine.plan.status == "PENDING"
    
    # Speed up execution for tests by setting duration to very small values
    for action in engine.plan.actions:
        action.duration = 0.05
        
    events = []
    def progress_callback(action, event_type, progress):
        events.append((action.name, event_type, progress))
        
    engine.execute(progress_callback=progress_callback)
    
    assert engine.plan.status == "COMPLETED"
    assert engine.plan.total_mttr >= 0
    assert len(events) > 0
    
    # Check that both actions went through START, PROGRESS, COMPLETED
    start_events = [e for e in events if e[1] == "START"]
    completed_events = [e for e in events if e[1] == "COMPLETED"]
    assert len(start_events) == 2
    assert len(completed_events) == 2
