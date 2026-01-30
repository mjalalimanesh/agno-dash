"""
Analyze Results Tool
====================

Provides insights from query results, not just raw data.

This is a key differentiator from basic text-to-SQL: the agent should
help users understand their data, not just return tables.

Features:
- Key findings summary
- Basic statistics for numeric columns
- Formatted results table
- Suggested follow-up questions
"""

from typing import Any, Optional

from agno.tools import tool


@tool
def analyze_results(
    results: list[dict[str, Any]],
    question: str,
    sql_query: str,
    context: Optional[str] = None,
) -> str:
    """Analyze query results and provide insights.

    Call this tool after executing a SQL query to provide users with
    meaningful insights rather than just raw data.

    Args:
        results: The query results as a list of dictionaries (rows).
        question: The original natural language question from the user.
        sql_query: The SQL query that produced these results.
        context: Optional additional context about the query or data.

    Returns:
        str: A formatted analysis with key findings, statistics, and follow-up suggestions.

    Example:
        analyze_results(
            results=[{"driver": "Hamilton", "wins": 11}, {"driver": "Bottas", "wins": 4}],
            question="Who won the most races in 2019?",
            sql_query="SELECT name, COUNT(*) AS wins FROM race_wins...",
            context="This shows race wins, not championship points"
        )
    """
    if not results:
        return _format_empty_results(question, sql_query)

    analysis_parts = []

    # Header
    analysis_parts.append("## Analysis")
    analysis_parts.append("")

    # Key findings
    key_findings = _extract_key_findings(results, question)
    analysis_parts.append("### Key Findings")
    for finding in key_findings:
        analysis_parts.append(f"- {finding}")
    analysis_parts.append("")

    # Statistics for numeric columns
    stats = _compute_statistics(results)
    if stats:
        analysis_parts.append("### Statistics")
        for col_name, col_stats in stats.items():
            analysis_parts.append(f"**{col_name}:**")
            for stat_name, stat_value in col_stats.items():
                analysis_parts.append(f"  - {stat_name}: {stat_value}")
        analysis_parts.append("")

    # Results table (limited)
    analysis_parts.append("### Results")
    analysis_parts.append(_format_results_table(results, max_rows=10))
    analysis_parts.append("")

    # Context if provided
    if context:
        analysis_parts.append("### Context")
        analysis_parts.append(context)
        analysis_parts.append("")

    # Follow-up suggestions
    follow_ups = _suggest_follow_ups(results, question)
    if follow_ups:
        analysis_parts.append("### Suggested Follow-up Questions")
        for follow_up in follow_ups:
            analysis_parts.append(f"- {follow_up}")

    return "\n".join(analysis_parts)


def _format_empty_results(question: str, sql_query: str) -> str:
    """Format response for empty results with actionable suggestions."""
    return f"""## No Results Found

The query returned no results. This could mean:

1. **Data doesn't exist**: There may be no data matching your criteria
2. **Filter too restrictive**: The WHERE conditions may be excluding all rows
3. **Data quality issue**: Column types or formats may not match expectations

### Suggestions

- Check if the table contains any data for the time period/filters specified
- Verify column types (e.g., position might be TEXT not INTEGER)
- For dates, ensure proper parsing (e.g., TO_DATE for text date columns)
- Try a broader query first to confirm data exists

### Query Used
```sql
{sql_query}
```

Would you like me to investigate why no results were returned?"""


def _extract_key_findings(results: list[dict[str, Any]], question: str) -> list[str]:
    """Extract key findings from results based on the question."""
    findings = []

    if not results:
        return ["No data found matching the criteria"]

    # Total count
    findings.append(f"Found {len(results)} result(s)")

    # If we have a small result set, highlight the top result
    if len(results) > 0:
        first = results[0]
        # Find the most likely "name" and "value" columns
        name_cols = [k for k in first.keys() if k.lower() in ("name", "driver", "team", "venue")]
        value_cols = [
            k for k in first.keys() if k.lower() in ("wins", "championships", "points", "count", "total", "podiums")
        ]

        if name_cols and value_cols:
            name_col = name_cols[0]
            value_col = value_cols[0]
            findings.append(f"Top result: {first[name_col]} with {first[value_col]} {value_col}")
        elif name_cols:
            name_col = name_cols[0]
            findings.append(f"Top result: {first[name_col]}")

    # If comparing (multiple results), note the range
    if len(results) >= 2:
        numeric_cols = [k for k, v in results[0].items() if isinstance(v, (int, float)) and v is not None]
        for col in numeric_cols[:1]:  # Just the first numeric column
            values = [r.get(col) for r in results if r.get(col) is not None]
            if values:
                min_val = min(values)
                max_val = max(values)
                if min_val != max_val:
                    findings.append(f"Range of {col}: {min_val} to {max_val}")

    return findings


def _compute_statistics(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute basic statistics for numeric columns."""
    if not results:
        return {}

    stats = {}
    numeric_cols = []

    # Find numeric columns
    for key, value in results[0].items():
        if isinstance(value, (int, float)) and value is not None:
            numeric_cols.append(key)

    for col in numeric_cols:
        values = [r.get(col) for r in results if r.get(col) is not None and isinstance(r.get(col), (int, float))]
        if not values:
            continue

        col_stats = {
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

        # Add average if we have enough values
        if len(values) >= 2:
            col_stats["average"] = round(sum(values) / len(values), 2)

        # Add sum for countable things
        if col.lower() in ("wins", "championships", "points", "count", "total", "podiums", "laps"):
            col_stats["total"] = sum(values)

        stats[col] = col_stats

    return stats


def _format_results_table(results: list[dict[str, Any]], max_rows: int = 10) -> str:
    """Format results as a markdown table."""
    if not results:
        return "_No results_"

    # Limit rows
    display_results = results[:max_rows]
    truncated = len(results) > max_rows

    # Get column names
    columns = list(display_results[0].keys())

    # Build header
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    # Build rows
    rows = []
    for result in display_results:
        values = [str(result.get(col, "")) for col in columns]
        rows.append("| " + " | ".join(values) + " |")

    table = "\n".join([header, separator] + rows)

    if truncated:
        table += f"\n\n_Showing {max_rows} of {len(results)} results_"

    return table


def _suggest_follow_ups(results: list[dict[str, Any]], question: str) -> list[str]:
    """Suggest relevant follow-up questions based on results."""
    suggestions = []
    question_lower = question.lower()

    # Time-based follow-ups
    if "year" in question_lower or "2019" in question_lower or "2020" in question_lower:
        suggestions.append("How does this compare to previous years?")

    # Driver-related follow-ups
    if "driver" in question_lower or "who" in question_lower:
        suggestions.append("Which team were they driving for?")
        if "win" in question_lower:
            suggestions.append("How many championships have they won?")

    # Team-related follow-ups
    if "team" in question_lower or "constructor" in question_lower:
        suggestions.append("Which drivers contributed to this?")
        suggestions.append("How has their performance changed over time?")

    # Generic follow-ups
    if len(results) > 1:
        suggestions.append("Can you show this as a trend over time?")

    # Limit suggestions
    return suggestions[:3]
