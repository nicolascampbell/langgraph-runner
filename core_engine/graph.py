from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core_engine.state import AgentState
from core_engine.nodes import create_node_function

def execute_graph(
    graph_payload: Dict[str, Any],
    agents: List[Dict[str, Any]],
    resources: List[Dict[str, Any]],
    context_data: str,
    run_id: str = "",
) -> str:
    """
    Constructs and executes a LangGraph based on the database's Graph Payload (nodes and edges).
    """
    print(f"Initializing Dynamic LangGraph...")
    
    # 1. Structure the resources map
    agents_map = {agent["id"]: agent for agent in agents}
    resources_map = {res["id"]: res for res in resources}
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    nodes = graph_payload.get("nodes", [])
    edges = graph_payload.get("edges", [])
    
    # 2. Add nodes dynamically
    node_ids = []
    for node in nodes:
        node_id = node.get("id")
        if node_id:
            node_ids.append(node_id)
            # Create a callable function specific to this node's configuration
            node_function = create_node_function(node)
            workflow.add_node(node_id, node_function)
    
    # 3. Add edges dynamically
    if not nodes:
        print("No nodes found in graph payload.")
        return "Graph had no nodes to execute."
        
    if not edges:
        # If there are no edges but there are nodes, maybe just run the first node and end
        # Or run them sequentially if that's the default. Let's assume a basic single node start graph:
        workflow.add_edge(START, node_ids[0])
        workflow.add_edge(node_ids[0], END)
        
    else:
        # Process the custom JSONB edges
        has_start = False
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            
            if source == "START" or not source:
                 workflow.add_edge(START, target)
                 has_start = True
            elif target == "END" or not target:
                 workflow.add_edge(source, END)
            else:
                 workflow.add_edge(source, target)
                 
        if not has_start and node_ids:
            # Fallback Start Edge
            workflow.add_edge(START, node_ids[0])
            
        # You'll also need a fallback END edge for nodes that have no outgoing connections in a real scenario
        # workflow.add_edge(final_node, END)
        pass # Simplified for scaffolding

    # Compile the graph
    app = workflow.compile()
    
    # Set the initial state
    initial_state = {
        "messages": [],
        "context": context_data,
        "run_id": run_id,
        "node_outputs": {},
        "graph_payload": graph_payload,
        "agents": agents_map,
        "resources": resources_map,
    }
    
    print("Executing compiled LangGraph...")
    result = app.invoke(initial_state, {"recursion_limit": 25})
    
    # Join formatted per-node outputs for the final response
    return "\n".join(result["node_outputs"].values())
