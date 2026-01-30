"""
Semantic Model (Layer 1)
========================

Builds table metadata context from knowledge files.

This is the foundation of the agent's understanding of the database schema.
Each table definition includes:
- Table name and description
- Column names, types, and descriptions
- Data quality notes (critical for correct SQL generation)
- Use cases and related tables
"""

import json
from pathlib import Path
from typing import Any

from agno.utils.log import logger

# Knowledge is at repo root level (../../knowledge from da/context/)
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"
TABLES_DIR = KNOWLEDGE_DIR / "tables"


def load_table_metadata(tables_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load table metadata from JSON files.

    Args:
        tables_dir: Directory containing table JSON files.
                   Defaults to knowledge/tables/

    Returns:
        List of table metadata dictionaries.
    """
    if tables_dir is None:
        tables_dir = TABLES_DIR

    tables = []
    if not tables_dir.exists():
        logger.warning(f"Tables directory not found: {tables_dir}")
        return tables

    for filepath in sorted(tables_dir.glob("*.json")):
        try:
            with open(filepath) as f:
                table = json.load(f)

            tables.append(
                {
                    "table_name": table["table_name"],
                    "description": table.get("table_description", ""),
                    "columns": table.get("table_columns", []),
                    "use_cases": table.get("use_cases", []),
                    "data_quality_notes": table.get("data_quality_notes", []),
                    "related_tables": table.get("related_tables", []),
                }
            )
        except Exception as e:
            logger.error(f"Failed to load table metadata from {filepath}: {e}")

    return tables


def build_semantic_model(tables_dir: Path | None = None) -> dict[str, Any]:
    """Build complete semantic model from table metadata.

    Args:
        tables_dir: Directory containing table JSON files.

    Returns:
        Semantic model dictionary with tables list.
    """
    return {"tables": load_table_metadata(tables_dir)}


def format_semantic_model(model: dict[str, Any]) -> str:
    """Format semantic model as human-readable text for system prompt.

    The output is optimized for LLM consumption:
    - Clear section headers
    - Prominent data quality warnings
    - Structured column information

    Args:
        model: Semantic model dictionary.

    Returns:
        Formatted string for system prompt.
    """
    lines = []

    for table in model.get("tables", []):
        table_name = table["table_name"]
        description = table.get("description", "")

        lines.append(f"### {table_name}")
        if description:
            lines.append(description)
        lines.append("")

        # Data quality notes (most important - put first)
        quality_notes = table.get("data_quality_notes", [])
        if quality_notes:
            lines.append("**DATA QUALITY NOTES (CRITICAL):**")
            for note in quality_notes:
                lines.append(f"  - {note}")
            lines.append("")

        # Columns
        columns = table.get("columns", [])
        if columns:
            lines.append("**Columns:**")
            for col in columns:
                col_name = col.get("name", "?")
                col_type = col.get("type", "unknown")
                col_desc = col.get("description", "")
                lines.append(f"  - `{col_name}` ({col_type}): {col_desc}")
            lines.append("")

        # Use cases
        use_cases = table.get("use_cases", [])
        if use_cases:
            lines.append("**Use cases:** " + ", ".join(use_cases))
            lines.append("")

    return "\n".join(lines)


# Pre-built model for import convenience
SEMANTIC_MODEL = build_semantic_model()
SEMANTIC_MODEL_STR = format_semantic_model(SEMANTIC_MODEL)
