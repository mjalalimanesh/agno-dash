#!/usr/bin/env python3
"""Basic SQL safety checks for Dash skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

DESTRUCTIVE_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke)\b",
    re.IGNORECASE,
)

SELECT_PATTERN = re.compile(r"^\s*select\b", re.IGNORECASE)
LIMIT_PATTERN = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)
SELECT_STAR_PATTERN = re.compile(r"\bselect\s+\*", re.IGNORECASE)


def _clean_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def check_query_safety(sql: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    cleaned = _clean_sql(sql)
    if not cleaned:
        errors.append("SQL is empty.")
        return {"ok": False, "errors": errors, "warnings": warnings}

    destructive_hits = sorted({m.lower() for m in DESTRUCTIVE_PATTERN.findall(cleaned)})
    if destructive_hits:
        errors.append(
            "Destructive or write operations detected: "
            + ", ".join(destructive_hits)
            + "."
        )

    if ";" in cleaned.rstrip(";"):
        warnings.append("Multiple SQL statements detected; prefer a single statement.")

    if SELECT_PATTERN.search(cleaned):
        if not LIMIT_PATTERN.search(cleaned):
            warnings.append("Missing LIMIT clause. Add LIMIT 50 by default.")
        if SELECT_STAR_PATTERN.search(cleaned):
            warnings.append("Avoid SELECT *; specify explicit columns.")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check SQL safety for Dash read-only analytics usage."
    )
    parser.add_argument(
        "--sql",
        help="SQL statement to validate. If omitted, SQL is read from stdin.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sql = args.sql if args.sql is not None else sys.stdin.read()
    result = check_query_safety(sql)
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
