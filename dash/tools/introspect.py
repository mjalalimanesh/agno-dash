"""Runtime schema inspection (Layer 6)."""

from agno.tools import tool
from agno.utils.log import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DatabaseError, OperationalError

# Internal / system schemas that should never be surfaced to the agent.
_EXCLUDED_SCHEMAS = frozenset(
    {
        "information_schema",
        "pg_catalog",
        "pg_toast",
        "pg_internal",
    }
)


def create_introspect_schema_tool(registry: dict[str, str]):
    """Create introspect_schema tool with analytics database registry."""
    engines = {name: create_engine(url) for name, url in registry.items()}
    db_names = list(engines.keys())
    default_db = db_names[0] if len(db_names) == 1 else None

    def _resolve(database: str | None):
        name = (database or default_db or "").lower()
        if name not in engines:
            raise ValueError(
                f"Unknown database '{name}'. Available: {', '.join(db_names)}"
            )
        return name, engines[name]

    @tool
    def introspect_schema(
        table_name: str | None = None,
        schema: str | None = None,
        include_sample_data: bool = False,
        sample_limit: int = 5,
        database: str | None = None,
    ) -> str:
        """Inspect database schema at runtime.

        When called without table_name, lists all tables across all schemas.

        Args:
            table_name: Table to inspect. If None, lists all tables.
            schema: Schema the table belongs to (e.g. "dbo", "sales").
                Optional — defaults to listing/inspecting the default schema.
            include_sample_data: Include sample rows.
            sample_limit: Number of sample rows.
            database: Logical database name (e.g. "main", "sales").
                Optional if only one analytics DB is configured.
        """
        try:
            db_name, engine = _resolve(database)
            insp = inspect(engine)

            # --- List tables mode ---
            if table_name is None:
                # If a specific schema is requested, only list that one
                if schema:
                    schemas_to_scan = [schema]
                else:
                    schemas_to_scan = [
                        s
                        for s in insp.get_schema_names()
                        if s not in _EXCLUDED_SCHEMAS
                    ]

                lines = [f"## Tables ({db_name})", ""]
                total_tables = 0
                for s in sorted(schemas_to_scan):
                    tables = insp.get_table_names(schema=s)
                    if not tables:
                        continue
                    total_tables += len(tables)
                    lines.append(f"### Schema: `{s}`")
                    for t in sorted(tables):
                        try:
                            qualified = f'"{s}"."{t}"'
                            with engine.connect() as conn:
                                count = conn.execute(
                                    text(f"SELECT COUNT(*) FROM {qualified}")
                                ).scalar()
                                lines.append(f"- **{t}** ({count:,} rows)")
                        except (OperationalError, DatabaseError):
                            lines.append(f"- **{t}**")
                    lines.append("")

                if total_tables == 0:
                    return f"No tables found in '{db_name}'."
                return "\n".join(lines)

            # --- Describe single table mode ---
            # Verify table exists in the given (or default) schema
            tables = insp.get_table_names(schema=schema)
            if table_name not in tables:
                # Build a helpful error that lists available tables
                available = ", ".join(sorted(tables)) if tables else "(none)"
                schema_label = f"schema '{schema}'" if schema else "default schema"
                return (
                    f"Table '{table_name}' not found in {schema_label} "
                    f"of '{db_name}'. Available: {available}"
                )

            qualified = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'
            lines = [f"## {table_name} ({db_name}" + (f" / {schema})" if schema else ")"), ""]

            cols = insp.get_columns(table_name, schema=schema)
            if cols:
                lines.extend(
                    [
                        "### Columns",
                        "",
                        "| Column | Type | Nullable |",
                        "| --- | --- | --- |",
                    ]
                )
                for c in cols:
                    nullable = "Yes" if c.get("nullable", True) else "No"
                    lines.append(
                        f"| {c['name']} | {c['type']} | {nullable} |"
                    )
                lines.append("")

            pk = insp.get_pk_constraint(table_name, schema=schema)
            if pk and pk.get("constrained_columns"):
                lines.append(
                    f"**Primary Key:** {', '.join(pk['constrained_columns'])}"
                )
                lines.append("")

            if include_sample_data:
                lines.append("### Sample")
                try:
                    with engine.connect() as conn:
                        result = conn.execute(
                            text(
                                f"SELECT * FROM {qualified} "
                                f"LIMIT {sample_limit}"
                            )
                        )
                        rows = result.fetchall()
                        col_names = list(result.keys())
                        if rows:
                            lines.append(
                                "| " + " | ".join(col_names) + " |"
                            )
                            lines.append(
                                "| "
                                + " | ".join(["---"] * len(col_names))
                                + " |"
                            )
                            for row in rows:
                                vals = [
                                    str(v)[:30] if v else "NULL" for v in row
                                ]
                                lines.append("| " + " | ".join(vals) + " |")
                        else:
                            lines.append("_No data_")
                except (OperationalError, DatabaseError) as e:
                    lines.append(f"_Error: {e}_")

            return "\n".join(lines)

        except ValueError as e:
            return str(e)
        except OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            return f"Error: Database connection failed - {e}"
        except DatabaseError as e:
            logger.error(f"Database error: {e}")
            return f"Error: {e}"

    return introspect_schema
