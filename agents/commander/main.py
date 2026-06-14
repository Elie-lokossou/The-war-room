import uuid
from lib.band_client import BandClientWrapper
from lib.models import IncidentAlert, TriageTask

band = BandClientWrapper()


def handle_alert(envelope):
    payload = envelope["payload"]
    alert = IncidentAlert(**payload)
    incident_id = f"inc-{str(uuid.uuid4())[:8]}"

    for agent in ["@metrics-agent", "@logs-agent", "@change-agent", "@runbook-agent"]:
        task = TriageTask(
            task_id=str(uuid.uuid4())[:8],
            incident_id=incident_id,
            assigned_to=agent,
            description=f"Triage {alert.title}: {alert.description}",
        )
        band.publish("triage-tasks", task.model_dump(), "commander")
        band.send_message(
            "triage-tasks",
            f"{agent} triage task assigned",
            mentions=[agent],
        )


def start():
    band.subscribe("incident-events", handle_alert)
    while True:
        band.poll("incident-events")
