from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class AgentConfig(BaseModel):
    id: str
    name: str
    role: str
    system_prompt: str
    model_provider: str
    model_name: str
    temperature: float

class ResourceConfig(BaseModel):
    id: str
    type: str
    name: str
    description: str
    connection_string: Optional[str] = None
    auth_token: Optional[str] = None

class GraphPayload(BaseModel):
    nodes: List[Dict[str, Any]]  # The tasks/steps and which agent runs them
    edges: List[Dict[str, Any]]  # The execution flow between nodes

class RunRequest(BaseModel):
    run_id: str
    mission_id: str
    graph: GraphPayload
    agents: List[AgentConfig]
    resources: List[ResourceConfig]
    # Briefing / Context docs (from mission_artifacts)
    s3_context_links: List[str] = []
