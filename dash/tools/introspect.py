"""Runtime schema inspection (Layer 6)."""

from agno.tools import tool
from agno.utils.log import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DatabaseError, OperationalError


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
        include_sample_data: bool = False,
        sample_limit: int = 5,
        database: str | None = None,
    ) -> str:
        """Inspect database schema at runtime.

        Args:
            table_name: Table to inspect. If None, lists all tables.
            include_sample_data: Include sample rows.
            sample_limit: Number of sample rows.
            database: Logical database name (e.g. "main", "sales").
                Optional if only one analytics DB is configured.
        """
        try:
            db_name, engine = _resolve(database)
            insp = inspect(engine)

            if table_name is None:
                tables = insp.get_table_names()
                if not tables:
                    return f"No tables found in '{db_name}'."

                lines = [f"## Tables ({db_name})", ""]
                for t in sorted(tables):
                    try:
                        with engine.connect() as conn:
                            count = conn.execute(
                                text(f'SELECT COUNT(*) FROM "{t}"')
                            ).scalar()
                            lines.append(f"- **{t}** ({count:,} rows)")
                    except (OperationalError, DatabaseError):
                        lines.append(f"- **{t}**")
                return "\n".join(lines)

            tables = insp.get_table_names()
            if table_name not in tables:
                return (
                    f"Table '{table_name}' not found in '{db_name}'. "
                    f"Available: {', '.join(sorted(tables))}"
                )

            lines = [f"## {table_name} ({db_name})", ""]

            cols = insp.get_columns(table_name)
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

            pk = insp.get_pk_constraint(table_name)
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
                                f'SELECT * FROM "{table_name}" '
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
