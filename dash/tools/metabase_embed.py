"""Secure Metabase signed-embed helpers and tool."""

from __future__ import annotations

from datetime import datetime, timezone
from os import getenv
from time import time
from typing import Any

import jwt
from agno.run import RunContext
from agno.tools import tool
from agno.utils.log import log_warning

DEFAULT_EMBED_TTL_SECONDS = 900
MIN_EMBED_TTL_SECONDS = 60
MAX_EMBED_TTL_SECONDS = 3600


def _env_or_default(name: str, default: str) -> str:
    value = getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _normalize_site_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    if not normalized:
        raise RuntimeError("Metabase embed URL is not configured.")
    if not normalized.startswith(("http://", "https://")):
        raise RuntimeError("Metabase embed URL must start with http:// or https://.")
    return normalized


def _parse_ttl_seconds() -> int:
    raw = _env_or_default("METABASE_EMBED_TTL_SECONDS", str(DEFAULT_EMBED_TTL_SECONDS))
    try:
        ttl = int(raw)
    except ValueError as exc:
        raise RuntimeError("METABASE_EMBED_TTL_SECONDS must be an integer.") from exc
    if ttl < MIN_EMBED_TTL_SECONDS:
        return MIN_EMBED_TTL_SECONDS
    if ttl > MAX_EMBED_TTL_SECONDS:
        return MAX_EMBED_TTL_SECONDS
    return ttl


def _parse_allowed_question_ids() -> set[int] | None:
    raw = _env_or_default("METABASE_ALLOWED_QUESTION_IDS", "")
    if not raw:
        return None

    allowlist: set[int] = set()
    for token in raw.split(","):
        item = token.strip()
        if not item:
            continue
        try:
            question_id = int(item)
        except ValueError as exc:
            raise RuntimeError(
                "METABASE_ALLOWED_QUESTION_IDS must be a comma-separated list of integers."
            ) from exc
        if question_id <= 0:
            raise RuntimeError("METABASE_ALLOWED_QUESTION_IDS values must be positive integers.")
        allowlist.add(question_id)

    return allowlist if allowlist else None


def is_metabase_embedding_configured() -> bool:
    """Return True when minimum signed-embed settings are present."""
    site_url = _env_or_default("METABASE_SITE_URL", _env_or_default("METABASE_URL", ""))
    embed_secret = _env_or_default("METABASE_EMBED_SECRET", "")
    return bool(site_url and embed_secret)


def build_metabase_question_embed(question_id: int, title: str | None = None) -> dict[str, Any]:
    """Create a signed Metabase embed payload for a question/card."""
    if question_id <= 0:
        raise ValueError("question_id must be a positive integer.")

    allowlist = _parse_allowed_question_ids()
    if allowlist is not None and question_id not in allowlist:
        raise PermissionError(
            f"Question {question_id} is not permitted by METABASE_ALLOWED_QUESTION_IDS."
        )

    site_url = _normalize_site_url(
        _env_or_default("METABASE_SITE_URL", _env_or_default("METABASE_URL", ""))
    )
    embed_secret = _env_or_default("METABASE_EMBED_SECRET", "")
    if not embed_secret:
        raise RuntimeError("METABASE_EMBED_SECRET is not configured.")

    ttl_seconds = _parse_ttl_seconds()
    expires_at = int(time()) + ttl_seconds
    payload = {
        "resource": {"question": question_id},
        "params": {},
        "exp": expires_at,
    }
    token = jwt.encode(payload, embed_secret, algorithm="HS256")

    embed: dict[str, Any] = {
        "kind": "metabase_question",
        "question_id": question_id,
        "iframe_url": f"{site_url}/embed/question/{token}#bordered=true&titled=true",
        "open_url": f"{site_url}/question/{question_id}",
        "expires_at": expires_at,
    }
    if title:
        clean_title = title.strip()
        if clean_title:
            embed["title"] = clean_title

    return embed


def _upsert_embed(existing: Any, embed: dict[str, Any]) -> list[dict[str, Any]]:
    embeds: list[dict[str, Any]] = []
    if isinstance(existing, list):
        for item in existing:
            if not isinstance(item, dict):
                continue
            if item.get("kind") != "metabase_question":
                embeds.append(item)
                continue
            if item.get("question_id") != embed["question_id"]:
                embeds.append(item)
    embeds.append(embed)
    return embeds


def _save_embed_in_context(run_context: RunContext, embed: dict[str, Any]) -> None:
    if run_context.metadata is None:
        run_context.metadata = {}
    run_context.metadata["embeds"] = _upsert_embed(run_context.metadata.get("embeds"), embed)

    if run_context.session_state is None:
        run_context.session_state = {}
    run_context.session_state["metabase_embeds"] = _upsert_embed(
        run_context.session_state.get("metabase_embeds"), embed
    )


def create_metabase_question_embed_tool():
    """Create a tool that signs Metabase question embeds and stores payload in run metadata."""

    @tool
    def create_metabase_question_embed(
        run_context: RunContext,
        question_id: int,
        title: str | None = None,
    ) -> str:
        """Create a secure signed embed payload for a Metabase question (card).

        Args:
            question_id: Metabase question/card id.
            title: Optional display title for UI cards.
        """
        try:
            embed = build_metabase_question_embed(question_id=question_id, title=title)
            _save_embed_in_context(run_context, embed)
            expires_human = datetime.fromtimestamp(embed["expires_at"], tz=timezone.utc).isoformat()
            return (
                f"Prepared secure embed metadata for question {question_id}. "
                f"Token expires at {expires_human}. "
                "Do not print signed URLs in plain response text."
            )
        except PermissionError as exc:
            log_warning(str(exc))
            return "Embed not permitted for this question."
        except Exception as exc:
            log_warning(f"Failed to create Metabase embed metadata: {exc}")
            return "Failed to create Metabase embed metadata."

    return create_metabase_question_embed
