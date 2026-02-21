"""
Dash AgentOS
========

Production deployment entry point for Dash.

Run:
    python -m app.main
"""

import hmac
from os import getenv
from pathlib import Path

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from agno.os import AgentOS
from agno.utils.log import log_warning

from dash.agent import dash
from dash.tools import build_metabase_question_embed, is_metabase_embedding_configured
from db import get_postgres_db

# ============================================================================
# Create AgentOS
# ============================================================================
agent_os = AgentOS(
    name="Dash",
    agents=[dash],
    tracing=True,
    scheduler=True,
    db=get_postgres_db(),
    config=str(Path(__file__).parent / "config.yaml"),
    # Allow the agent UI to connect from any origin (e.g. VM IP)
    cors_allowed_origins=["*"],
)

app = agent_os.get_app()


class MetabaseEmbedRefreshRequest(BaseModel):
    question_id: int = Field(gt=0)
    title: str | None = None


class MetabaseEmbedRefreshResponse(BaseModel):
    kind: str
    question_id: int
    iframe_url: str
    open_url: str
    expires_at: int
    title: str | None = None


def _require_embed_refresh_auth(request: Request) -> None:
    """Require Authorization when OS_SECURITY_KEY is configured."""
    os_security_key = getenv("OS_SECURITY_KEY", "").strip()
    if not os_security_key:
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    provided_key = auth_header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(provided_key, os_security_key):
        raise HTTPException(status_code=403, detail="Invalid bearer token.")


@app.post(
    "/api/metabase/embed/refresh",
    response_model=MetabaseEmbedRefreshResponse,
)
async def refresh_metabase_question_embed(
    payload: MetabaseEmbedRefreshRequest,
    request: Request,
) -> MetabaseEmbedRefreshResponse:
    _require_embed_refresh_auth(request)
    if not is_metabase_embedding_configured():
        raise HTTPException(
            status_code=503,
            detail="Metabase embedding is not configured on the server.",
        )

    try:
        embed = build_metabase_question_embed(
            question_id=payload.question_id,
            title=payload.title,
        )
    except PermissionError as exc:
        log_warning(f"Metabase embed refresh permission error: {exc}")
        raise HTTPException(status_code=403, detail="Embed is not permitted.") from exc
    except ValueError as exc:
        log_warning(f"Metabase embed refresh validation error: {exc}")
        raise HTTPException(status_code=400, detail="Invalid embed request.") from exc
    except RuntimeError as exc:
        log_warning(f"Metabase embed refresh runtime error: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Metabase embedding is unavailable.",
        ) from exc

    return MetabaseEmbedRefreshResponse(**embed)


if __name__ == "__main__":
    agent_os.serve(
        app="main:app",
        reload=getenv("RUNTIME_ENV", "prd") == "dev",
    )
