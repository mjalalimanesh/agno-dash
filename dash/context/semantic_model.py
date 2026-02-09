"""Load table metadata for the system prompt."""

import json
from pathlib import Path
from typing import Any

from agno.utils.log import logger

from dash.paths import TABLES_DIR

MAX_QUALITY_NOTES = 5


def load_table_metadata(tables_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load table metadata from JSON files."""
    if tables_dir is None:
        tables_dir = TABLES_DIR

    tables: list[dict[str, Any]] = []
    if not tables_dir.exists():
        return tables

    for filepath in sorted(tables_dir.glob("*.json")):
        try:
            with open(filepath) as f:
                table = json.load(f)
            tables.append(
                {
                    "table_name": table["table_name"],
                    "description": table.get("table_description", ""),
                    "use_cases": table.get("use_cases", []),
                    "data_quality_notes": table.get("data_quality_notes", [])[:MAX_QUALITY_NOTES],
                    "database": table.get("database"),
                }
            )
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.error(f"Failed to load {filepath}: {e}")

    return tables


def build_semantic_model(tables_dir: Path | None = None) -> dict[str, Any]:
    """Build semantic model from table metadata."""
    return {"tables": load_table_metadata(tables_dir)}


def format_semantic_model(model: dict[str, Any]) -> str:
    """Format semantic model for system prompt. Groups tables by database when present."""
    tables = model.get("tables", [])
    if not tables:
        return ""

    # Group by database: None/missing -> "all", else by database name
    by_db: dict[str | None, list[dict[str, Any]]] = {}
    for t in tables:
        db = t.get("database")
        by_db.setdefault(db, []).append(t)

    lines: list[str] = []
    # Tables with a database first (sorted by db name), then tables applicable to all
    for db in sorted(k for k in by_db if k is not None):
        lines.append(f"### Database: **{db}**")
        lines.append("")
        for table in by_db[db]:
            lines.append(f"#### {table['table_name']}")
            if table.get("description"):
                lines.append(table["description"])
            if table.get("use_cases"):
                lines.append(f"**Use cases:** {', '.join(table['use_cases'])}")
            if table.get("data_quality_notes"):
                lines.append("**Data quality:**")
                for note in table["data_quality_notes"]:
                    lines.append(f"  - {note}")
            lines.append("")
    for table in by_db.get(None, []):
        lines.append(f"### {table['table_name']}")
        if table.get("description"):
            lines.append(table["description"])
        if table.get("use_cases"):
            lines.append(f"**Use cases:** {', '.join(table['use_cases'])}")
        if table.get("data_quality_notes"):
            lines.append("**Data quality:**")
            for note in table["data_quality_notes"]:
                lines.append(f"  - {note}")
        lines.append("")

    return "\n".join(lines)


SEMANTIC_MODEL = build_semantic_model()
SEMANTIC_MODEL_STR = format_semantic_model(SEMANTIC_MODEL)
