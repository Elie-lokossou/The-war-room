from pydantic import BaseModel
from typing import List, Any, Optional

class Evidence(BaseModel):
    id: str
    source: str
    content: Any

class IncidentAlert(BaseModel):
    id: str
    title: str
    description: str
    severity: str

class TriageTask(BaseModel):
    task_id: str
    incident_id: str
    assigned_to: str
    description: str

class Finding(BaseModel):
    finding_id: str
    task_id: str
    summary: str
    evidence: List[Evidence]

class DeliberationMessage(BaseModel):
    message_id: str
    sender: str
    content: str

class CommanderVerdict(BaseModel):
    incident_id: str
    verdict: str
    actions_to_take: List[str]
