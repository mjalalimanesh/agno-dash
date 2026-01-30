"""
Query Patterns (Layer 3)
========================

Loads validated SQL query patterns from knowledge files.

These are queries that have been:
1. Executed successfully
2. Validated by a human
3. Saved for future reuse

The patterns include metadata like:
- What question they answer
- Which tables they use
- Data quality considerations
"""

import re
from dataclasses import dataclass
from pathlib import Path

from agno.utils.log import logger

# Knowledge is at repo root level (../../knowledge from da/context/)
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"
QUERIES_DIR = KNOWLEDGE_DIR / "queries"


@dataclass
class QueryPattern:
    """A validated SQL query pattern.

    Attributes:
        name: Short identifier for the query
        description: What the query does
        query: The SQL query text
        tables: Tables used by the query
        data_quality_notes: Special considerations
    """

    name: str
    description: str
    query: str
    tables: list[str]
    data_quality_notes: str | None = None


def load_query_patterns(queries_dir: Path | None = None) -> list[QueryPattern]:
    """Load query patterns from SQL files.

    SQL files should use comment annotations:
        -- <query name>query_name</query name>
        -- <query description>
        -- Description of what the query does
        -- </query description>
        -- <query>
        SELECT ...
        -- </query>

    Args:
        queries_dir: Directory containing SQL files.
                    Defaults to knowledge/queries/

    Returns:
        List of QueryPattern objects.
    """
    if queries_dir is None:
        queries_dir = QUERIES_DIR

    patterns = []

    if not queries_dir.exists():
        logger.warning(f"Queries directory not found: {queries_dir}")
        return patterns

    for filepath in sorted(queries_dir.glob("*.sql")):
        try:
            with open(filepath) as f:
                content = f.read()

            # Parse multiple queries from one file
            file_patterns = _parse_sql_file(content)
            patterns.extend(file_patterns)

        except Exception as e:
            logger.error(f"Failed to load query patterns from {filepath}: {e}")

    return patterns


def _parse_sql_file(content: str) -> list[QueryPattern]:
    """Parse query patterns from SQL file content.

    Uses XML-style tags in comments to extract metadata.
    """
    patterns = []

    # Pattern to match query blocks
    # Matches: -- <query name>NAME</query name> ... -- <query>SQL</query>
    query_pattern = re.compile(
        r"--\s*<query name>([^<]+)</query name>\s*\n"
        r"(.*?)"
        r"--\s*<query>\s*\n"
        r"(.*?)"
        r"--\s*</query>",
        re.DOTALL | re.IGNORECASE,
    )

    for match in query_pattern.finditer(content):
        name = match.group(1).strip()
        metadata = match.group(2).strip()
        query = match.group(3).strip()

        # Extract description from metadata
        desc_match = re.search(
            r"--\s*<query description>\s*\n(.*?)--\s*</query description>",
            metadata,
            re.DOTALL | re.IGNORECASE,
        )
        description = ""
        if desc_match:
            # Clean up description (remove comment prefixes)
            desc_lines = desc_match.group(1).strip().split("\n")
            description = " ".join(line.lstrip("-").strip() for line in desc_lines if line.strip())

        # Extract tables (simple heuristic - look for FROM/JOIN)
        tables = _extract_tables(query)

        patterns.append(
            QueryPattern(
                name=name,
                description=description,
                query=query,
                tables=tables,
            )
        )

    return patterns


def _extract_tables(query: str) -> list[str]:
    """Extract table names from SQL query.

    Simple heuristic: looks for FROM and JOIN keywords.
    """
    tables = []

    # Normalize whitespace
    query = " ".join(query.split())

    # Pattern for FROM table and JOIN table
    from_pattern = re.compile(r"\bFROM\s+(\w+)", re.IGNORECASE)
    join_pattern = re.compile(r"\bJOIN\s+(\w+)", re.IGNORECASE)

    for match in from_pattern.finditer(query):
        table = match.group(1).lower()
        if table not in tables:
            tables.append(table)

    for match in join_pattern.finditer(query):
        table = match.group(1).lower()
        if table not in tables:
            tables.append(table)

    return tables


def format_query_patterns(patterns: list[QueryPattern]) -> str:
    """Format query patterns for system prompt or knowledge base.

    Args:
        patterns: List of QueryPattern objects.

    Returns:
        Formatted string with all patterns.
    """
    lines = ["## VALIDATED QUERY PATTERNS", ""]

    for pattern in patterns:
        lines.append(f"### {pattern.name}")
        if pattern.description:
            lines.append(pattern.description)
        if pattern.tables:
            lines.append(f"**Tables:** {', '.join(pattern.tables)}")
        lines.append("```sql")
        lines.append(pattern.query)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


# Pre-loaded patterns for import convenience
QUERY_PATTERNS = load_query_patterns()
