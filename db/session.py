"""
Database Session
================

PostgreSQL database connection for AgentOS.
"""

from typing import Any

from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.pgvector import PgVector, SearchType

from db.url import db_url

DB_ID = "dash-db"


def get_postgres_db(contents_table: str | None = None) -> PostgresDb:
    """Create a PostgresDb instance.

    Args:
        contents_table: Optional table name for storing knowledge contents.

    Returns:
        Configured PostgresDb instance.
    """
    if contents_table is not None:
        return PostgresDb(id=DB_ID, db_url=db_url, knowledge_table=contents_table)
    return PostgresDb(id=DB_ID, db_url=db_url)


def create_knowledge(
    name: str,
    table_name: str,
    embedder_id: str = "text-embedding-3-small",
    embedder_api_key: str | None = None,
    embedder_base_url: str | None = None,
) -> Knowledge:
    """Create a Knowledge instance with PgVector hybrid search."""
    embedder_kwargs: dict[str, Any] = {"id": embedder_id}
    if embedder_api_key:
        embedder_kwargs["api_key"] = embedder_api_key
    if embedder_base_url:
        embedder_kwargs["base_url"] = embedder_base_url

    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(**embedder_kwargs),
        ),
        contents_db=get_postgres_db(contents_table=f"{table_name}_contents"),
    )
