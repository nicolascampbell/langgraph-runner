"""
MCP client for workmate-runner.

Opens stdio MCP server subprocesses, loads their tools into LangChain,
and sanitizes tool schemas for OpenAI compatibility.

Usage (inside an async node function):
    async with mcp_tools_context(mcp_resources) as tools:
        result = await agent.ainvoke({"messages": messages})
"""
import os
from contextlib import asynccontextmanager, AsyncExitStack
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools


def _fix_schema(schema: dict) -> dict:
    """Recursively add missing 'items' to array-type fields (OpenAI requirement)."""
    if not isinstance(schema, dict):
        return schema
    if schema.get("type") == "array" and "items" not in schema:
        schema["items"] = {}
    for value in schema.values():
        if isinstance(value, dict):
            _fix_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _fix_schema(item)
    return schema


def _sanitize_tools(tools):
    for tool in tools:
        if hasattr(tool, "args_schema") and isinstance(tool.args_schema, dict):
            _fix_schema(tool.args_schema)
    return tools


@asynccontextmanager
async def _single_mcp_session(resource: Dict[str, Any]):
    """Spawn one MCP server subprocess and yield its tools."""
    import json as _json

    command_str = resource.get("connection_string", "")
    parts = command_str.split(" ", 1)
    command = parts[0]
    args = [parts[1]] if len(parts) > 1 else []

    # auth_token may carry a JSON dict of extra env vars for this MCP server
    env = {**os.environ}
    auth_token = resource.get("auth_token")
    if auth_token:
        try:
            extra_env = _json.loads(auth_token)
            if isinstance(extra_env, dict):
                env.update(extra_env)
        except Exception:
            pass

    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = _sanitize_tools(await load_mcp_tools(session))
            print(f" - MCP: loaded {len(tools)} tool(s) from '{resource.get('name')}'")
            yield tools


@asynccontextmanager
async def mcp_tools_context(mcp_resources: List[Dict[str, Any]]):
    """
    Open connections to all MCP server resources and yield a combined tool list.
    All subprocess connections stay alive for the duration of the async with block.
    """
    async with AsyncExitStack() as stack:
        all_tools = []
        for resource in mcp_resources:
            tools = await stack.enter_async_context(_single_mcp_session(resource))
            all_tools.extend(tools)
        yield all_tools
