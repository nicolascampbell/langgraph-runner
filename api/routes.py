from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from services.s3_service import retrieve_s3_data
from core_engine.graph import execute_graph

router = APIRouter()

# Schema representation based on Database Models
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

@router.post("/run")
async def execute_run(request: RunRequest):
    try:
        # 1. Retrieve Context from S3 (Looping through artifacts)
        context_data = ""
        for link in request.s3_context_links:
             context_data += f"\n--- {link} ---\n"
             context_data += retrieve_s3_data(link)
             context_data += "\n"
        
        # 2. Execute LangGraph multi-agent system based on GraphPayload
        # We pass the full graph structure (nodes/edges), defined agents, and tools (resources)
        result = execute_graph(
            graph_payload=request.graph.model_dump(),
            agents=[agent.model_dump() for agent in request.agents],
            resources=[res.model_dump() for res in request.resources],
            context_data=context_data
        )
        
        return {
            "status": "success",
            "run_id": request.run_id,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
