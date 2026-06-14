from enum import IntEnum
from typing import Any, Dict, List
from pydantic import BaseModel

class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Evidence(BaseModel):
    id: str
    source: str
    content: Any

class IncidentAlert(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity

class TriageTask(BaseModel):
    task_id: str
    incident_id: str
    assigned_to: str
    description: str
    data_path: str = ""
    time_window: str = ""

class Finding(BaseModel):
    finding_id: str
    task_id: str
    agent: str = ""
    finding_type: str = "observation"
    signal: str = ""
    value: str = ""
    confidence: float = 0.0
    hypothesis: str = ""
    summary: str
    evidence: List[Evidence] = []
    supporting_data: Dict[str, Any] = {}

class DeliberationMessage(BaseModel):
    message_id: str
    sender: str
    content: str

class CommanderVerdict(BaseModel):
    incident_id: str
    verdict: str
    actions_to_take: List[str]
