from fastapi import APIRouter, HTTPException

from services.s3_service import retrieve_s3_data
from services.db_service import (
    fetch_graph_payload,
    create_run_record,
    update_run_status,
    write_run_log,
)
from core_engine.graph import execute_graph
from api.schemas import RunRequest

router = APIRouter()


@router.post("/run")
async def execute_run(request: RunRequest):
    run_id = request.run_id
    mission_id = request.mission_id

    try:
        # 1. Fetch graph definition, agents, and resources from the DB
        payload = fetch_graph_payload(mission_id)
        graph_version = payload.get("graph_version")

        # 2. Create run record in DB
        create_run_record(run_id, mission_id, graph_version)

        # 3. Retrieve context from S3
        context_data = ""
        for link in (request.s3_context_links or []):
            context_data += f"\n--- {link} ---\n"
            context_data += retrieve_s3_data(link)
            context_data += "\n"

        # 4. Execute LangGraph multi-agent workflow
        result = execute_graph(
            graph_payload={"nodes": payload["nodes"], "edges": payload["edges"]},
            agents=payload["agents"],
            resources=payload["resources"],
            context_data=context_data,
            run_id=run_id,
        )

        # 5. Mark run as completed
        update_run_status(run_id, "completed", result_summary=result[:500] if result else None)

        return {"status": "success", "run_id": run_id, "result": result}

    except Exception as e:
        # Best-effort: log to DB, then propagate
        try:
            write_run_log(run_id, None, "error", str(e))
            update_run_status(run_id, "failed", result_summary=str(e)[:500])
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
