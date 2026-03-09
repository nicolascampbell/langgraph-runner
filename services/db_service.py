"""
PostgreSQL service layer for workmate-runner.
Fetches graph definitions, agents, and resources; persists run + node execution records.
Requires DATABASE_URL environment variable.
"""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras


def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(url)


def fetch_graph_payload(mission_id: str) -> Dict[str, Any]:
    """
    Fetch the active graph (nodes + edges) plus all agents and resources for a mission.
    Returns a dict with keys: graph_id, graph_version, nodes, edges, agents, resources.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, nodes, edges, version FROM graphs "
                "WHERE mission_id = %s AND is_active = TRUE LIMIT 1",
                (mission_id,),
            )
            graph = cur.fetchone()
            if not graph:
                raise ValueError(f"No active graph found for mission_id={mission_id!r}")

            cur.execute(
                "SELECT id, name, role, system_prompt, model_provider, model_name, temperature "
                "FROM agents WHERE mission_id = %s",
                (mission_id,),
            )
            agents: List[Dict] = [dict(row) for row in cur.fetchall()]

            cur.execute(
                "SELECT id, type, name, description, connection_string, auth_token "
                "FROM resources WHERE mission_id = %s",
                (mission_id,),
            )
            resources: List[Dict] = [dict(row) for row in cur.fetchall()]

    return {
        "graph_id": graph["id"],
        "graph_version": graph.get("version"),
        "nodes": graph["nodes"] or [],
        "edges": graph["edges"] or [],
        "agents": agents,
        "resources": resources,
    }


def create_run_record(run_id: str, mission_id: str, graph_version: Optional[int]) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO runs (id, mission_id, graph_version, status, started_at) "
                "VALUES (%s, %s, %s, 'running', NOW())",
                (run_id, mission_id, graph_version),
            )
        conn.commit()


def update_run_status(
    run_id: str, status: str, result_summary: Optional[str] = None
) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE runs SET status = %s, result_summary = %s, finished_at = NOW() "
                "WHERE id = %s",
                (status, result_summary, run_id),
            )
        conn.commit()


def write_node_execution(
    run_id: str,
    node_id: str,
    output_content: str,
    started_at: datetime,
    finished_at: datetime,
    token_usage: Optional[Dict] = None,
) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO node_executions "
                "(run_id, node_id, status, output_content, started_at, finished_at, token_usage) "
                "VALUES (%s, %s, 'completed', %s, %s, %s, %s)",
                (
                    run_id,
                    node_id,
                    output_content,
                    started_at,
                    finished_at,
                    psycopg2.extras.Json(token_usage) if token_usage else None,
                ),
            )
        conn.commit()


def write_run_log(
    run_id: str, node_id: Optional[str], level: str, message: str
) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO run_logs (run_id, node_id, level, message, timestamp) "
                "VALUES (%s, %s, %s, %s, NOW())",
                (run_id, node_id, level, message),
            )
        conn.commit()
