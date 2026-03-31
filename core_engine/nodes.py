from datetime import datetime, timezone
from typing import Dict, Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from core_engine.state import AgentState
from core_engine.llm import get_llm
from core_engine.tools.registry import load_tools
from core_engine.tools.mcp_client import mcp_tools_context


def create_node_function(node_config: Dict[str, Any]):
    """
    Creates an async node function attached to the LangGraph execution flow.
    Handles both regular tools (sync-loaded) and MCP tools (async subprocess).
    """
    node_id = node_config.get("id")
    agent_id = node_config.get("agent_id")
    task_instructions = node_config.get("instructions", "No instructions provided.")
    resource_ids = node_config.get("resource_ids")  # None means "all resources"

    async def process_node(state: AgentState):
        run_id = state.get("run_id", "")

        agent_config = state["agents"].get(agent_id, {})
        agent_name = agent_config.get("name", "Unknown Agent")
        model_provider = agent_config.get("model_provider", "openai")
        model_name = agent_config.get("model_name", "gpt-4o-mini")
        temperature = agent_config.get("temperature", 0.7)
        system_prompt = agent_config.get("system_prompt", "You are a helpful assistant.")

        print(f"\n[{agent_name}] executing Node {node_id} using {model_provider} ({model_name})...")

        llm = get_llm(provider=model_provider, model_name=model_name, temperature=temperature)

        messages = (
            [SystemMessage(content=system_prompt)]
            + state.get("messages", [])
            + [HumanMessage(content=f"Context Document:\n{state['context']}\n\nTask: {task_instructions}")]
        )

        # Split resources into MCP (async subprocess) and regular (sync-loaded)
        resources_dict = state.get("resources", {})
        if resource_ids is not None:
            resources_list = [resources_dict[rid] for rid in resource_ids if rid in resources_dict]
        else:
            resources_list = list(resources_dict.values())

        mcp_resources = [r for r in resources_list if r.get("type") == "mcp"]
        sync_resources = [r for r in resources_list if r.get("type") != "mcp"]
        sync_tools = load_tools(sync_resources)

        started_at = datetime.now(timezone.utc)
        token_usage = None

        try:
            if mcp_resources:
                async with mcp_tools_context(mcp_resources) as mcp_tool_list:
                    all_tools = sync_tools + mcp_tool_list
                    result_content, token_usage = await _invoke_agent(llm, messages, all_tools)
            else:
                result_content, token_usage = await _invoke_agent(llm, messages, sync_tools)

        except Exception as e:
            _safe_write_log(run_id, node_id, "error", str(e))
            raise

        finished_at = datetime.now(timezone.utc)

        formatted_response = (
            f"--- Node: {node_id} | Agent: {agent_name} | Engine: {model_provider} ---\n"
            f"{result_content}\n"
        )

        _safe_write_node_execution(run_id, node_id, formatted_response, started_at, finished_at, token_usage)

        new_outputs = state.get("node_outputs", {}).copy()
        new_outputs[node_id] = formatted_response

        return {
            "messages": [AIMessage(content=result_content, name=node_id)],
            "node_outputs": new_outputs,
        }

    return process_node


async def _invoke_agent(llm, messages, tools):
    """Run the LLM — with a ReAct agent loop if tools are present, directly otherwise."""
    if tools:
        print(f" -> Equipping {len(tools)} tool(s). Starting ReAct Agent loop...")
        agent = create_agent(llm, tools)
        response = await agent.ainvoke({"messages": messages}, {"recursion_limit": 10})
        last_msg = response["messages"][-1]
        token_usage = getattr(last_msg, "usage_metadata", None)
        return last_msg.content, token_usage
    else:
        print(" -> No tools equipped. Using direct LLM invocation...")
        response = await llm.ainvoke(messages)
        token_usage = getattr(response, "usage_metadata", None)
        return response.content, token_usage


def _safe_write_node_execution(run_id, node_id, output, started_at, finished_at, token_usage):
    if not run_id:
        return
    try:
        from services.db_service import write_node_execution
        write_node_execution(run_id, node_id, output, started_at, finished_at, token_usage)
    except Exception as ex:
        print(f" [DB] Failed to write node_execution for {node_id}: {ex}")


def _safe_write_log(run_id, node_id, level, message):
    if not run_id:
        return
    try:
        from services.db_service import write_run_log
        write_run_log(run_id, node_id, level, message)
    except Exception as ex:
        print(f" [DB] Failed to write run_log for {node_id}: {ex}")
