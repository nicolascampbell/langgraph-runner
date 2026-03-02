from typing import TypedDict, Annotated, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    The state shared across all nodes in the graphs.
    """
    messages: Annotated[list, add_messages]
    context: str

    # We can store the current outputs of previous nodes to be passed to future nodes
    node_outputs: Dict[str, Any]

    # Store the actual DB graph payload and agents for reference during execution
    graph_payload: Dict[str, Any]
    agents: Dict[str, Any] # Keyed by agent ID
    resources: Dict[str, Any] # Keyed by resource ID
