"""POST /api/run — invoke LangGraph pipeline and stream SSE events.

SSE event types (per PRD §7.2):
    agent_step  — {agent, status, ts, ...}
    plan        — {plan: {...}}
    done        — terminal
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_session
from models import Plan, Profile, Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["run"])


def _sse_event(data: dict[str, Any]) -> str:
    """Format a dict as a Server-Sent Event data line."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("/run")
async def run_graph(
    request: Request,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the LangGraph pipeline for the current session.

    Returns a streaming SSE response with agent_step events,
    the final plan, and a done event.
    """
    # Load profile for this session
    profile_row = await db.get(Profile, session.id)
    if profile_row is None:
        raise HTTPException(
            status_code=400,
            detail="No profile found for this session. Complete intake first.",
        )

    profile_json: dict[str, Any] = dict(profile_row.profile_json)
    seeker_type: str = profile_row.seeker_type

    # Include seeker_type in profile for agents that read it from there
    profile_json["seeker_type"] = seeker_type

    # Initial graph state
    initial_state = {
        "profile": profile_json,
        "seeker_type": seeker_type,
        "scheme_out": [],
        "job_out": [],
        "housing_out": [],
        "validator_out": {},
        "plan": {},
        "errors": [],
        "agent_steps": [],
    }

    # Build graph
    import sys
    packages_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "packages"))
    if packages_dir not in sys.path:
        sys.path.insert(0, packages_dir)

    from agents.graph import build_graph

    graph = build_graph()

    # Capture session_id for plan persistence
    session_id = session.id

    async def event_generator():
        """Async generator that streams SSE events as the graph executes."""
        emitted_steps: set[str] = set()
        final_output: dict[str, Any] = {}

        try:
            # astream yields {node_name: partial_state_update} per node
            async for chunk in graph.astream(initial_state):
                for node_name, node_output in chunk.items():
                    if not isinstance(node_output, dict):
                        continue

                    # Merge node output into running final state
                    final_output.update(node_output)

                    # Emit any new agent_steps from this node
                    for step in node_output.get("agent_steps", []):
                        step_key = f"{step.get('agent')}_{step.get('status')}"
                        if step_key not in emitted_steps:
                            emitted_steps.add(step_key)
                            yield _sse_event(step)

            # Extract the final plan
            plan = final_output.get("plan", {})
            plan_row_id = None

            # Persist plan to database
            try:
                from database import async_session_factory
                async with async_session_factory() as plan_db:
                    plan_row = Plan(
                        id=uuid.uuid4(),
                        session_id=session_id,
                        plan_json=plan,
                        agent_trace_json={
                            "steps": final_output.get("agent_steps", []),
                            "errors": final_output.get("errors", []),
                        },
                        filtered_out_json=plan.get("filtered_out"),
                        llm_profile=os.getenv("LLM_PROFILE", "dev"),
                    )
                    plan_db.add(plan_row)
                    await plan_db.commit()
                    plan_row_id = str(plan_row.id)
                    logger.info("Plan saved: id=%s, session=%s", plan_row.id, session_id)
            except Exception as exc:
                logger.error("Failed to persist plan: %s", exc)

            # Emit the plan event
            yield _sse_event({
                "type": "plan",
                "plan": plan,
                "plan_id": plan_row_id,
            })

            # Emit errors if any
            errors = final_output.get("errors", [])
            if errors:
                yield _sse_event({"type": "errors", "errors": errors})

            # Done
            yield _sse_event({"type": "done"})

        except Exception as exc:
            logger.exception("Graph execution failed: %s", exc)
            yield _sse_event({
                "type": "error",
                "message": str(exc),
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            yield _sse_event({"type": "done"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
