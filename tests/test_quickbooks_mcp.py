"""
Test QuickBooks MCP server integration with a LangGraph agent.
Spawns the QB MCP server via stdio and runs a simple query.
"""
import sys
import os
import asyncio
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import dotenv_values, load_dotenv
load_dotenv()  # load runner's .env (OPENAI_API_KEY etc.)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from core_engine.llm import get_llm


def fix_schema(schema: dict) -> dict:
    """Recursively add missing 'items' to array-type fields in a JSON schema."""
    if not isinstance(schema, dict):
        return schema
    if schema.get("type") == "array" and "items" not in schema:
        schema["items"] = {}
    for value in schema.values():
        if isinstance(value, dict):
            fix_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    fix_schema(item)
    return schema


def sanitize_tools(tools):
    for tool in tools:
        if hasattr(tool, "args_schema") and isinstance(tool.args_schema, dict):
            fix_schema(tool.args_schema)
        elif hasattr(tool, "args_schema") and hasattr(tool.args_schema, "schema"):
            fix_schema(tool.args_schema.schema())
    return tools

QB_REPO = r"F:\Nico\Work\Vincent\mcp servers\quickbooks\quickbooks-online-mcp-server"
QB_MCP_PATH = QB_REPO + r"\dist\index.js"

# Merge current env with QB-specific credentials
QB_ENV = {**os.environ, **dotenv_values(QB_REPO + r"\.env")}

async def main():
    print("Connecting to QuickBooks MCP server...")

    server_params = StdioServerParameters(
        command="node",
        args=[QB_MCP_PATH],
        env=QB_ENV,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = sanitize_tools(await load_mcp_tools(session))
            print(f"Loaded {len(tools)} tools from QB MCP server:")
            for t in tools:
                print(f"  - {t.name}")

            print("\nRunning agent query...")
            llm = get_llm("openai", "gpt-4o-mini", 0.0)
            agent = create_agent(llm, tools)

            result = await agent.ainvoke({
                "messages": "List the first 5 customers in QuickBooks."
            })

            final = result["messages"][-1].content
            print(f"\nAgent response:\n{final}")

if __name__ == "__main__":
    asyncio.run(main())
