"""Read-only analytics SQL tools: thin wrappers around Agno SQLTools with database routing."""

import json

from agno.tools import tool
from agno.tools.sql import SQLTools
from agno.utils.log import log_debug, logger
from sqlalchemy.inspection import inspect

WRITE_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
}

# Internal / system schemas that should never be surfaced to the agent.
_EXCLUDED_SCHEMAS = frozenset(
    {
        "information_schema",
        "pg_catalog",
        "pg_toast",
        "pg_internal",
    }
)


def create_analytics_sql_tools(registry: dict[str, str]) -> list:
    """Create read-only SQL tool wrappers backed by Agno SQLTools instances."""
    sql_tools_map: dict[str, SQLTools] = {
        name: SQLTools(db_url=url) for name, url in registry.items()
    }
    db_names = list(sql_tools_map.keys())
    default_db = db_names[0] if len(db_names) == 1 else None

    def _resolve(database: str | None) -> SQLTools:
        name = (database or default_db or "").lower()
        if name not in sql_tools_map:
            raise ValueError(
                f"Unknown database '{name}'. Available: {', '.join(db_names)}"
            )
        return sql_tools_map[name]

    def _reject_writes(sql: str) -> None:
        tokens = sql.strip().split()
        first_token = tokens[0].lower() if tokens else ""
        if first_token in WRITE_KEYWORDS:
            raise ValueError(
                "Write operations are not allowed on analytics databases."
            )

    @tool
    def list_tables(database: str | None = None) -> str:
        """List all tables across all schemas in an analytics database.

        Returns a JSON object mapping each schema to its list of tables,
        e.g. {"public": ["t1"], "sales": ["orders", "customers"]}.

        Args:
            database: Logical database name (e.g. "main", "sales").
                Optional if only one analytics DB is configured.
        """
        try:
            log_debug("listing tables across all schemas")
            engine = _resolve(database).db_engine
            inspector = inspect(engine)
            schemas = [
                s for s in inspector.get_schema_names() if s not in _EXCLUDED_SCHEMAS
            ]
            result: dict[str, list[str]] = {}
            for schema in schemas:
                tables = inspector.get_table_names(schema=schema)
                if tables:
                    result[schema] = tables
            log_debug(f"tables by schema: {result}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return f"Error getting tables: {e}"

    @tool
    def describe_table(
        table_name: str,
        database: str | None = None,
        schema: str | None = None,
    ) -> str:
        """Describe a table's columns and types.

        Args:
            table_name: Name of the table to describe.
            database: Logical database name.
            schema: Schema the table belongs to (e.g. "dbo", "sales").
                Optional — defaults to the database's default schema.
        """
        try:
            log_debug(f"Describing table: {table_name} (schema={schema})")
            engine = _resolve(database).db_engine
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name, schema=schema)
            return json.dumps(
                [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                    }
                    for col in columns
                ]
            )
        except Exception as e:
            logger.error(f"Error getting table schema: {e}")
            return f"Error getting table schema: {e}"

    @tool
    def run_sql_query(query: str, database: str | None = None) -> str:
        """Run a read-only SQL query on an analytics database.

        Args:
            query: SQL SELECT query to execute.
            database: Logical database name.
        """
        _reject_writes(query)
        return _resolve(database).run_sql_query(query)

    return [list_tables, describe_table, run_sql_query]
