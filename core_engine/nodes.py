from core_engine.state import AgentState
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from core_engine.tools.registry import load_tools
import os

# Import Provider LLMs
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(provider: str, model_name: str, temperature: float):
    """
    Dynamic factory that returns the appropriate LangChain Chat model
    based on the requested provider. Falls back to OpenAI if the provider's
    API key is missing from the environment.
    """
    provider = provider.lower().strip()
    
    # Check for keys
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if provider == "anthropic" and anthropic_key:
         return ChatAnthropic(
             model_name=model_name,
             temperature=temperature,
             api_key=anthropic_key
         )
    elif provider == "google" and google_key:
         return ChatGoogleGenerativeAI(
             model=model_name,
             temperature=temperature,
             api_key=google_key
         )
    elif provider == "openai" and openai_key:
         return ChatOpenAI(
             model=model_name,
             temperature=temperature,
             api_key=openai_key
         )
    else:
         # Fallback to OpenAI if a key is missing or provider is unknown
         print(f"Warning: Provider '{provider}' requested but key is missing (or provider unknown). Falling back to OpenAI gpt-4o-mini.")
         return ChatOpenAI(
             model="gpt-4o-mini",
             temperature=temperature,
             api_key=openai_key
         )

def create_node_function(node_config: Dict[str, Any]):
    """
    Creates a node function that will be attached to the LangGraph execution flow.
    The node config comes from the JSONB 'nodes' payload from the DB.
    """
    node_id = node_config.get("id")
    agent_id = node_config.get("agent_id")
    task_instructions = node_config.get("instructions", "No instructions provided.")
    
    def process_node(state: AgentState):
        """
        Dynamically processes a node based on its configuration, 
        using the specific agent and the shared context.
        """
        # Look up the agent config that is supposed to run this node
        agent_config = state["agents"].get(agent_id, {})
        agent_name = agent_config.get("name", "Unknown Agent")
        
        # Determine the model and provider
        model_provider = agent_config.get("model_provider", "openai")
        model_name = agent_config.get("model_name", "gpt-4o-mini")
        temperature = agent_config.get("temperature", 0.7)
        system_prompt = agent_config.get("system_prompt", "You are a helpful assistant.")
        
        print(f"\n[{agent_name}] executing Node {node_id} using {model_provider} ({model_name})...")
        
        # Dynamically instantiate the LLM
        llm = get_llm(
             provider=model_provider, 
             model_name=model_name, 
             temperature=temperature
        )
        
        # Construct the messages array
        messages = [
             SystemMessage(content=system_prompt),
             HumanMessage(content=f"Context Document:\n{state['context']}\n\nTask: {task_instructions}")
        ]
        
        # Load any dynamic tools from the global state/DB config
        resources_dict = state.get("resources", {})
        resources_list = list(resources_dict.values())
        tools = load_tools(resources_list)
        
        # Determine execution path 
        if tools:
             print(f" -> Equipping {len(tools)} tool(s). Starting ReAct Agent loop...")
             # create_react_agent builds a compiled LangGraph specifically for Tool usage
             agent_executor = create_react_agent(llm, tools=tools)
             # The executor takes our same messages array and runs autonomously 
             # until the tools finish and the LLM produces a final answer.
             response = agent_executor.invoke({"messages": messages})
             # create_react_agent returns a dict with the updated "messages" array. 
             # The final message is the LLM's conclusive response.
             result_content = response["messages"][-1].content
        else:
             print(" -> No tools equipped. Using direct LLM invocation...")
             # Direct invocation if no tools are available.
             response = llm.invoke(messages)
             result_content = response.content
        
        formatted_response = (
            f"--- Node: {node_id} | Agent: {agent_name} | Engine: {model_provider} ---\n"
            f"{result_content}\n"
        )
        
        # We can append the result to messages and to a specific node output map
        new_outputs = state.get("node_outputs", {}).copy()
        new_outputs[node_id] = formatted_response
        
        return {
            "messages": [formatted_response],
            "node_outputs": new_outputs
        }
        
    return process_node
