"""
Integration test script for workmate-runner.
Tests DB connectivity, graph execution, web search, and DB persistence.

Usage:
    venv/Scripts/python tests/test_integration.py
"""
import os
import sys
import json
import uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from services.db_service import (
    get_db_connection,
    fetch_graph_payload,
    create_run_record,
    update_run_status,
    write_node_execution,
    write_run_log,
)
from core_engine.graph import execute_graph

# ── Test mission IDs ────────────────────────────────────────────────────────
MISSION_ID     = "00000000-0000-0000-0000-000000000099"
AGENT_1        = "00000000-0000-0000-0001-000000000001"
AGENT_2        = "00000000-0000-0000-0001-000000000002"
WEB_SEARCH_RES = "00000000-0000-0000-0002-000000000001"

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


# ── 1. DB Connection ─────────────────────────────────────────────────────────
section("1. DB Connection")
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT version()")
    version = cur.fetchone()[0][:50]
    cur.close(); conn.close()
    print(f"{PASS} Connected: {version}")
except Exception as e:
    print(f"{FAIL} {e}")
    sys.exit(1)


# ── 2. Seed test mission ─────────────────────────────────────────────────────
section("2. Seed test mission in DB")
try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users LIMIT 1")
        user_id = cur.fetchone()[0]

        # Clear previous test data
        cur.execute("DELETE FROM graphs    WHERE mission_id = %s", (MISSION_ID,))
        cur.execute("DELETE FROM agents    WHERE mission_id = %s", (MISSION_ID,))
        cur.execute("DELETE FROM resources WHERE mission_id = %s", (MISSION_ID,))
        cur.execute("DELETE FROM missions  WHERE id = %s",         (MISSION_ID,))

        cur.execute(
            "INSERT INTO missions (id, owner_user_id, name) VALUES (%s, %s, %s)",
            (MISSION_ID, user_id, "Runner Integration Test"),
        )
        cur.execute(
            "INSERT INTO agents (id, mission_id, name, role, system_prompt, model_provider, model_name, temperature) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (AGENT_1, MISSION_ID, "Researcher", "Analyst",
             "You are a concise technical analyst.", "openai", "gpt-4o-mini", 0.3),
        )
        cur.execute(
            "INSERT INTO agents (id, mission_id, name, role, system_prompt, model_provider, model_name, temperature) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (AGENT_2, MISSION_ID, "Summariser", "Writer",
             "You write crisp one-sentence executive summaries.", "openai", "gpt-4o-mini", 0.3),
        )
        cur.execute(
            "INSERT INTO resources (id, mission_id, type, name, description) VALUES (%s,%s,%s,%s,%s)",
            (WEB_SEARCH_RES, MISSION_ID, "web_search", "Web Search", "DuckDuckGo search"),
        )
        conn.commit()
    print(f"{PASS} Mission, 2 agents, and web_search resource inserted")
except Exception as e:
    print(f"{FAIL} {e}")
    sys.exit(1)


# ── 3. fetch_graph_payload with a 2-node graph ───────────────────────────────
section("3. fetch_graph_payload")
TWO_NODE_GRAPH = {
    "nodes": [
        {"id": "task-research", "agent_id": AGENT_1,
         "instructions": "In 2-3 sentences, explain what LangGraph is."},
        {"id": "task-summary",  "agent_id": AGENT_2,
         "instructions": "Write a one-sentence executive summary of the previous output."},
    ],
    "edges": [
        {"source": "START",         "target": "task-research"},
        {"source": "task-research", "target": "task-summary"},
        {"source": "task-summary",  "target": "END"},
    ],
}
try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO graphs (mission_id, version, is_active, nodes, edges) VALUES (%s,1,TRUE,%s,%s)",
            (MISSION_ID, json.dumps(TWO_NODE_GRAPH["nodes"]), json.dumps(TWO_NODE_GRAPH["edges"])),
        )
        conn.commit()

    payload = fetch_graph_payload(MISSION_ID)
    assert len(payload["nodes"]) == 2, "Expected 2 nodes"
    assert len(payload["agents"]) == 2, "Expected 2 agents"
    assert len(payload["resources"]) == 1, "Expected 1 resource"
    print(f"{PASS} Fetched: {len(payload['nodes'])} nodes, "
          f"{len(payload['agents'])} agents, {len(payload['resources'])} resource")
except Exception as e:
    print(f"{FAIL} {e}")
    sys.exit(1)


# ── 4. 2-node graph execution (no tools) ─────────────────────────────────────
section("4. Two-node graph execution (no tools)")
run_id_basic = str(uuid.uuid4())
try:
    create_run_record(run_id_basic, MISSION_ID, payload["graph_version"])
    result = execute_graph(
        graph_payload={"nodes": TWO_NODE_GRAPH["nodes"], "edges": TWO_NODE_GRAPH["edges"]},
        agents=payload["agents"],
        resources=[],          # no tools for this test
        context_data="",
        run_id=run_id_basic,
    )
    update_run_status(run_id_basic, "completed", result[:500])
    assert "task-research" in result and "task-summary" in result
    print(f"{PASS} Graph executed, {len(result)} chars of output")
    print()
    print(result[:500])
except Exception as e:
    print(f"{FAIL} {e}")


# ── 5. Verify node_executions persisted ─────────────────────────────────────
section("5. node_executions persistence")
try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT node_id, status, length(output_content), token_usage "
            "FROM node_executions WHERE run_id = %s ORDER BY started_at",
            (run_id_basic,),
        )
        rows = cur.fetchall()
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    for node_id, status, length, token_usage in rows:
        has_tokens = token_usage is not None
        print(f"{PASS} {node_id}: status={status}, output={length} chars, token_usage={'yes' if has_tokens else 'no'}")
except Exception as e:
    print(f"{FAIL} {e}")


# ── 6. Web search tool (ReAct agent) ─────────────────────────────────────────
section("6. Web search tool (ReAct agent)")
run_id_search = str(uuid.uuid4())
WEB_SEARCH_NODES = [
    {
        "id": "task-search",
        "agent_id": AGENT_1,
        "resource_ids": [WEB_SEARCH_RES],
        "instructions": (
            "Use the web_search tool to find the current latest version of LangGraph. "
            "Report the version number and release date."
        ),
    }
]
WEB_SEARCH_EDGES = [
    {"source": "START",       "target": "task-search"},
    {"source": "task-search", "target": "END"},
]
try:
    create_run_record(run_id_search, MISSION_ID, payload["graph_version"])
    result_search = execute_graph(
        graph_payload={"nodes": WEB_SEARCH_NODES, "edges": WEB_SEARCH_EDGES},
        agents=payload["agents"],
        resources=payload["resources"],
        context_data="",
        run_id=run_id_search,
    )
    update_run_status(run_id_search, "completed", result_search[:500])
    print(f"{PASS} Web search agent completed")
    print()
    print(result_search[:600])
except Exception as e:
    print(f"{FAIL} {e}")


# ── 7. run_logs write ─────────────────────────────────────────────────────────
section("7. run_logs write")
try:
    write_run_log(run_id_basic, "task-research", "info", "Integration test log entry")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT level, message FROM run_logs WHERE run_id = %s", (run_id_basic,))
        log = cur.fetchone()
    assert log is not None
    print(f"{PASS} Log entry: level={log[0]}, message={log[1]!r}")
except Exception as e:
    print(f"{FAIL} {e}")


print(f"\n{'─' * 60}")
print("  All tests complete.")
print('─' * 60)
