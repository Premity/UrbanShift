"""LangGraph StateGraph — T16 wiring with conditional routing.

Graph topology:
    START → orchestrator_entry → scheme_node
        → (conditional on seeker_type) →
            job:     job_node     → validator_node → orchestrator_merge → END
            housing: housing_node → validator_node → orchestrator_merge → END
            both:    job_node → housing_node → validator_node → orchestrator_merge → END
"""

from __future__ import annotations

import logging
import operator
import os
import sys
from datetime import datetime, timezone
from typing import Annotated, Any

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)

# ── Ensure apps/api is on sys.path so model imports work ────────────────────
_API_DIR = os.environ.get("API_DIR", "/app")
if os.path.isdir(_API_DIR) and _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)
_LOCAL_API_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))
if os.path.isdir(_LOCAL_API_DIR) and _LOCAL_API_DIR not in sys.path:
    sys.path.insert(0, _LOCAL_API_DIR)


# ── Shared Graph State ──────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """Shared state flowing through the LangGraph pipeline."""
    profile: dict                                          # user profile dict
    seeker_type: str                                       # "job" | "housing" | "both"
    scheme_out: list[dict]                                 # scheme agent output
    job_out: list[dict]                                    # job agent output
    housing_out: list[dict]                                # housing agent output
    validator_out: dict                                    # {validated, filtered_out}
    plan: dict                                             # final merged plan
    errors: Annotated[list[str], operator.add]             # accumulated errors (reducer: append)
    agent_steps: Annotated[list[dict], operator.add]       # SSE step events (reducer: append)


# ── Step-event helper ───────────────────────────────────────────────────────

def _step_event(agent: str, status: str, **extra: Any) -> dict[str, Any]:
    """Create an agent_step event dict for SSE streaming."""
    event: dict[str, Any] = {
        "type": "agent_step",
        "agent": agent,
        "status": status,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    event.update(extra)
    return event


# ── Node wrappers ───────────────────────────────────────────────────────────
# Each wrapper adapts the existing agent function to the uniform
# (state: AgentState) -> partial-state-update signature.

async def _orchestrator_entry(state: AgentState) -> dict[str, Any]:
    from .orchestrator import orchestrator_entry_node
    return await orchestrator_entry_node(state)


async def _scheme_node(state: AgentState) -> dict[str, Any]:
    """Load all schemes from DB, run scheme agent, return scheme_out."""
    from database import async_session_factory
    from models.scheme import Scheme
    from sqlalchemy import select

    from .scheme_agent import run_scheme_agent

    profile = state.get("profile", {})
    seeker_type = state.get("seeker_type", "both")

    # Load all scheme rows from database
    async with async_session_factory() as db:
        result = await db.execute(select(Scheme))
        rows = result.scalars().all()

    all_schemes = []
    for row in rows:
        all_schemes.append({
            "id": row.id,
            "name": row.name,
            "level": row.level,
            "state": row.state,
            "category": row.category or [],
            "has_jobs": row.has_jobs,
            "eligibility_json": row.eligibility_json or {},
            "eligibility": row.eligibility_json or {},
            "docs_required": row.docs_required or [],
            "benefits_summary": row.benefits_summary or "",
            "benefits_detail_md": row.benefits_detail_md or "",
            "apply_link": row.apply_link,
            "source_url": row.source_url,
            "source_name": row.source_name,
            "embedding": row.embedding,
        })

    logger.info("Scheme node: loaded %d schemes from DB", len(all_schemes))

    # Run scheme agent
    agent_result = await run_scheme_agent(
        all_schemes=all_schemes,
        profile=profile,
        seeker_type=seeker_type,
    )

    schemes = agent_result.get("schemes", [])

    return {
        "scheme_out": schemes,
        "agent_steps": [
            _step_event("scheme", "running"),
            _step_event("scheme", "complete", items_count=len(schemes)),
        ],
    }


async def _job_node(state: AgentState) -> dict[str, Any]:
    """Run the job agent node."""
    from .job_agent import run_job_agent

    result = await run_job_agent(state)
    job_out = result.get("job_out", [])

    return {
        "job_out": job_out,
        "agent_steps": [
            _step_event("job", "running"),
            _step_event("job", "complete", items_count=len(job_out)),
        ],
    }


async def _housing_node(state: AgentState) -> dict[str, Any]:
    """Run the housing agent node."""
    from .housing_agent import housing_agent_node

    result = await housing_agent_node(state)
    housing_out = result.get("housing_out", [])

    existing_errors = state.get("errors", [])
    result_errors = result.get("errors", [])
    if len(result_errors) >= len(existing_errors):
        new_errors = result_errors[len(existing_errors):]
    else:
        new_errors = result_errors

    node_result: dict[str, Any] = {
        "housing_out": housing_out,
        "agent_steps": [
            _step_event("housing", "running"),
            _step_event("housing", "complete", items_count=len(housing_out)),
        ],
    }
    if new_errors:
        node_result["errors"] = new_errors
    return node_result


async def _validator_node(state: AgentState) -> dict[str, Any]:
    """Run the validator agent node."""
    from .validator_agent import validator_agent_node

    result = await validator_agent_node(state)
    validator_out = result.get("validator_out", {})
    validated = validator_out.get("validated", {})
    filtered_out = validator_out.get("filtered_out", [])

    kept = (
        len(validated.get("schemes", []))
        + len(validated.get("jobs", []))
        + len(validated.get("housing", []))
    )

    existing_errors = state.get("errors", [])
    result_errors = result.get("errors", [])
    if len(result_errors) >= len(existing_errors):
        new_errors = result_errors[len(existing_errors):]
    else:
        new_errors = result_errors

    node_result: dict[str, Any] = {
        "validator_out": validator_out,
        "agent_steps": [
            _step_event("validator", "running"),
            _step_event("validator", "complete", kept=kept, filtered=len(filtered_out)),
        ],
    }
    if new_errors:
        node_result["errors"] = new_errors
    return node_result


async def _orchestrator_merge(state: AgentState) -> dict[str, Any]:
    from .orchestrator import orchestrator_merge_node
    return await orchestrator_merge_node(state)


# ── Conditional routing ─────────────────────────────────────────────────────

def _route_after_scheme(state: AgentState) -> str:
    """Determine next node based on seeker_type."""
    seeker_type = state.get("seeker_type", "both")
    if seeker_type == "job":
        return "job_node"
    elif seeker_type == "housing":
        return "housing_node"
    else:  # "both"
        return "job_node"


def _route_after_job(state: AgentState) -> str:
    """After job node: go to housing if seeker_type is 'both', else validator."""
    seeker_type = state.get("seeker_type", "both")
    if seeker_type == "both":
        return "housing_node"
    else:
        return "validator_node"


# ── Graph Builder ───────────────────────────────────────────────────────────

def build_graph() -> Any:
    """Build and compile the LangGraph StateGraph.

    Returns a compiled graph ready for `graph.ainvoke(state)` or
    `graph.astream(state)`.
    """
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("orchestrator_entry", _orchestrator_entry)
    builder.add_node("scheme_node", _scheme_node)
    builder.add_node("job_node", _job_node)
    builder.add_node("housing_node", _housing_node)
    builder.add_node("validator_node", _validator_node)
    builder.add_node("orchestrator_merge", _orchestrator_merge)

    # Fixed edges
    builder.add_edge(START, "orchestrator_entry")
    builder.add_edge("orchestrator_entry", "scheme_node")

    # Conditional routing after scheme_node
    builder.add_conditional_edges(
        "scheme_node",
        _route_after_scheme,
        {
            "job_node": "job_node",
            "housing_node": "housing_node",
        },
    )

    # Conditional routing after job_node
    builder.add_conditional_edges(
        "job_node",
        _route_after_job,
        {
            "housing_node": "housing_node",
            "validator_node": "validator_node",
        },
    )

    # Housing always goes to validator
    builder.add_edge("housing_node", "validator_node")

    # Validator always goes to merge
    builder.add_edge("validator_node", "orchestrator_merge")

    # Merge is the end
    builder.add_edge("orchestrator_merge", END)

    # Compile
    graph = builder.compile()
    logger.info("LangGraph compiled: 6 nodes, conditional routing enabled")
    return graph
