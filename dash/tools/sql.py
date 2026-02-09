"""Read-only analytics SQL tools: thin wrappers around Agno SQLTools with database routing."""

from agno.tools import tool
from agno.tools.sql import SQLTools

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
        """List all tables in an analytics database.

        Args:
            database: Logical database name (e.g. "main", "sales").
                Optional if only one analytics DB is configured.
        """
        return _resolve(database).list_tables()

    @tool
    def describe_table(table_name: str, database: str | None = None) -> str:
        """Describe a table's columns and types.

        Args:
            table_name: Name of the table to describe.
            database: Logical database name.
        """
        return _resolve(database).describe_table(table_name)

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
