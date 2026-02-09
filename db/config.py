"""
Database configuration: internal DB vs analytics DB registry.
"""

import os

from db.url import db_url as internal_db_url


def get_internal_db_url() -> str:
    """Internal DB URL. Uses existing DB_* env vars. Always Postgres."""
    return internal_db_url


def get_analytics_registry() -> dict[str, str]:
    """Discover analytics DBs from ANALYTICS_DB_<NAME> env vars.

    Each value is a full SQLAlchemy URL:
      ANALYTICS_DB_MAIN=postgresql+psycopg://ro_user:pass@host:5432/f1
      ANALYTICS_DB_SALES=mssql+pyodbc://...

    Keys ending with _DESC are ignored (used for descriptions).
    Fallback: if none found, use internal DB_* as "default".
    """
    prefix = "ANALYTICS_DB_"
    suffix_desc = "_DESC"
    registry: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix) or not value:
            continue
        if key.endswith(suffix_desc):
            continue
        name = key[len(prefix) :].lower()
        registry[name] = value
    if not registry:
        registry["default"] = internal_db_url
    return registry


def get_analytics_descriptions() -> dict[str, str]:
    """Optional short descriptions for each analytics DB (for agent prompt).

    Reads env vars ANALYTICS_DB_<NAME>_DESC; the value is the description text.
    Returns dict mapping logical name (from the key) to description (from the value).
    E.g. ANALYTICS_DB_MAIN_DESC="F1 racing data" -> {"main": "F1 racing data"}.
    """
    prefix = "ANALYTICS_DB_"
    suffix = "_DESC"
    descriptions: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix) or not key.endswith(suffix) or not value:
            continue
        name = key[len(prefix) :].removesuffix(suffix).lower()
        descriptions[name] = value
    return descriptions
