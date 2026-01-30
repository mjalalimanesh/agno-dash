"""
Introspect Schema Tool
======================

Runtime schema inspection for Layer 6 context.

When knowledge base information is missing or stale, the agent can
use this tool to inspect the actual database schema at runtime.

Features:
- List all tables
- Show columns, types, nullable, primary keys
- Show foreign keys and indexes
- Optional sample data
"""

from typing import Any, Optional

from agno.tools import tool
from agno.utils.log import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

# Module-level engine reference (set by agent.py)
_db_engine: Optional[Engine] = None


def set_engine(db_url: str) -> None:
    """Set the database engine for introspection.

    Called by agent.py after initialization.
    """
    global _db_engine
    _db_engine = create_engine(db_url)


@tool
def introspect_schema(
    table_name: Optional[str] = None,
    include_sample_data: bool = False,
    sample_limit: int = 5,
) -> str:
    """Inspect database schema at runtime.

    Use this tool when knowledge base information is missing or potentially
    stale. This provides Layer 6 (Runtime Context) from the 6-layer
    context architecture.

    Args:
        table_name: Specific table to inspect. If None, lists all tables.
        include_sample_data: Whether to include sample rows (default False).
        sample_limit: Number of sample rows to return (default 5).

    Returns:
        str: Formatted schema information.

    Example:
        # List all tables
        introspect_schema()

        # Get details for a specific table
        introspect_schema(table_name="race_wins")

        # Get schema with sample data
        introspect_schema(table_name="race_wins", include_sample_data=True)
    """
    if _db_engine is None:
        return "Error: Database engine not initialized. Cannot inspect schema."

    try:
        inspector = inspect(_db_engine)

        if table_name is None:
            return _list_all_tables(inspector)
        else:
            return _inspect_table(inspector, table_name, include_sample_data, sample_limit)

    except Exception as e:
        logger.error(f"Schema introspection failed: {e}")
        return f"Error inspecting schema: {e}"


def _list_all_tables(inspector: Any) -> str:
    """List all tables in the database."""
    tables = inspector.get_table_names()

    if not tables:
        return "No tables found in the database."

    lines = ["## Database Tables", ""]
    for table in sorted(tables):
        # Get row count
        try:
            with _db_engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                lines.append(f"- **{table}** ({count:,} rows)")
        except Exception:
            lines.append(f"- **{table}**")

    lines.append("")
    lines.append("_Use `introspect_schema(table_name='...')` for detailed column information._")

    return "\n".join(lines)


def _inspect_table(
    inspector: Any,
    table_name: str,
    include_sample_data: bool,
    sample_limit: int,
) -> str:
    """Inspect a specific table's schema."""
    # Check if table exists
    tables = inspector.get_table_names()
    if table_name not in tables:
        return f"Error: Table '{table_name}' not found. Available tables: {', '.join(sorted(tables))}"

    lines = [f"## Table: {table_name}", ""]

    # Get columns
    columns = inspector.get_columns(table_name)
    if columns:
        lines.append("### Columns")
        lines.append("")
        lines.append("| Column | Type | Nullable | Default |")
        lines.append("| --- | --- | --- | --- |")
        for col in columns:
            name = col["name"]
            col_type = str(col["type"])
            nullable = "Yes" if col.get("nullable", True) else "No"
            default = str(col.get("default", "")) or "-"
            lines.append(f"| {name} | {col_type} | {nullable} | {default} |")
        lines.append("")

    # Get primary key
    pk = inspector.get_pk_constraint(table_name)
    if pk and pk.get("constrained_columns"):
        lines.append(f"**Primary Key:** {', '.join(pk['constrained_columns'])}")
        lines.append("")

    # Get foreign keys
    fks = inspector.get_foreign_keys(table_name)
    if fks:
        lines.append("### Foreign Keys")
        for fk in fks:
            referred_table = fk["referred_table"]
            local_cols = ", ".join(fk["constrained_columns"])
            referred_cols = ", ".join(fk["referred_columns"])
            lines.append(f"- {local_cols} -> {referred_table}({referred_cols})")
        lines.append("")

    # Get indexes
    indexes = inspector.get_indexes(table_name)
    if indexes:
        lines.append("### Indexes")
        for idx in indexes:
            idx_name = idx["name"]
            idx_cols = ", ".join(idx["column_names"])
            unique = " (unique)" if idx.get("unique") else ""
            lines.append(f"- **{idx_name}**: {idx_cols}{unique}")
        lines.append("")

    # Sample data
    if include_sample_data:
        lines.append("### Sample Data")
        lines.append("")
        try:
            with _db_engine.connect() as conn:
                result = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT {sample_limit}'))
                rows = result.fetchall()
                col_names = result.keys()

                if rows:
                    # Header
                    lines.append("| " + " | ".join(col_names) + " |")
                    lines.append("| " + " | ".join(["---"] * len(col_names)) + " |")

                    # Rows (truncate long values)
                    for row in rows:
                        values = []
                        for val in row:
                            str_val = str(val) if val is not None else "NULL"
                            if len(str_val) > 30:
                                str_val = str_val[:27] + "..."
                            values.append(str_val)
                        lines.append("| " + " | ".join(values) + " |")
                else:
                    lines.append("_No data in table_")
        except Exception as e:
            lines.append(f"_Error fetching sample data: {e}_")
        lines.append("")

    return "\n".join(lines)
