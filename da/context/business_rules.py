"""
Business Rules (Layer 2)
========================

Loads business definitions, metrics, and common gotchas.

This layer provides the "tribal knowledge" that makes the difference
between a query that technically runs and one that returns correct results.

Contents:
- Metric definitions (what "Race Win" means, how to calculate it)
- Business rules (Constructors Championship started in 1958)
- Common gotchas (position is TEXT in some tables, INTEGER in others)
"""

import json
from pathlib import Path
from typing import Any

from agno.utils.log import logger

# Knowledge is at repo root level (../../knowledge from da/context/)
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"
BUSINESS_DIR = KNOWLEDGE_DIR / "business"


def load_business_rules(business_dir: Path | None = None) -> dict[str, Any]:
    """Load business definitions from JSON files.

    Args:
        business_dir: Directory containing business JSON files.
                     Defaults to knowledge/business/

    Returns:
        Dictionary with metrics, business_rules, and common_gotchas.
    """
    if business_dir is None:
        business_dir = BUSINESS_DIR

    business = {
        "metrics": [],
        "business_rules": [],
        "common_gotchas": [],
    }

    if not business_dir.exists():
        logger.warning(f"Business directory not found: {business_dir}")
        return business

    for filepath in sorted(business_dir.glob("*.json")):
        try:
            with open(filepath) as f:
                data = json.load(f)

            if "metrics" in data:
                business["metrics"].extend(data["metrics"])
            if "business_rules" in data:
                business["business_rules"].extend(data["business_rules"])
            if "common_gotchas" in data:
                business["common_gotchas"].extend(data["common_gotchas"])

        except Exception as e:
            logger.error(f"Failed to load business rules from {filepath}: {e}")

    return business


def build_business_context(business_dir: Path | None = None) -> str:
    """Build business context string for system prompt.

    Args:
        business_dir: Directory containing business JSON files.

    Returns:
        Formatted string with metrics, rules, and gotchas.
    """
    business = load_business_rules(business_dir)
    lines = []

    # Metrics
    metrics = business.get("metrics", [])
    if metrics:
        lines.append("## METRICS")
        lines.append("")
        for metric in metrics:
            name = metric.get("name", "Unknown")
            definition = metric.get("definition", "")
            table = metric.get("table", "")
            calculation = metric.get("calculation", "")

            lines.append(f"**{name}**: {definition}")
            if table:
                lines.append(f"  - Table: `{table}`")
            if calculation:
                lines.append(f"  - Calculation: {calculation}")
            lines.append("")

    # Business rules
    rules = business.get("business_rules", [])
    if rules:
        lines.append("## BUSINESS RULES")
        lines.append("")
        for rule in rules:
            lines.append(f"- {rule}")
        lines.append("")

    # Common gotchas (most critical - emphasized)
    gotchas = business.get("common_gotchas", [])
    if gotchas:
        lines.append("## COMMON GOTCHAS (READ CAREFULLY!)")
        lines.append("")
        for gotcha in gotchas:
            issue = gotcha.get("issue", "Unknown issue")
            tables = gotcha.get("tables_affected", [])
            solution = gotcha.get("solution", "")

            lines.append(f"**{issue}**")
            if tables:
                lines.append(f"  - Tables: {', '.join(tables)}")
            if solution:
                lines.append(f"  - Solution: {solution}")
            lines.append("")

    return "\n".join(lines)


# Pre-built context for import convenience
BUSINESS_CONTEXT = build_business_context()
