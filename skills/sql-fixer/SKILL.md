---
name: sql-fixer
description: Diagnose and fix SQL generation and execution errors for Dash analytics queries. Use when a query fails due to schema mismatch, type mismatch, date parsing issues, unsafe SQL patterns, missing LIMIT/ORDER BY, or when converting a failure into reusable learning.
---

# SQL Fixer

Use this skill to recover quickly from SQL failures and keep future queries reliable.

## Fixing Workflow

1. Search context first:
   - Run `search_knowledge_base` for known query patterns.
   - Run `search_learnings` for prior fixes and gotchas.
2. Draft safe SQL:
   - Keep queries read-only.
   - Use explicit columns, not `SELECT *`.
   - Add `ORDER BY` for ranking requests.
   - Default to `LIMIT 50` unless the task needs a different limit.
3. If SQL fails:
   - Run `introspect_schema` for the affected table/database.
   - Correct types, column names, and date conversions.
   - Re-run the corrected query.
4. Persist what worked:
   - Save generalized error resolution via `save_learning`.
   - Offer `save_validated_query` for reusable query patterns.
5. Close with insight:
   - Explain what the result means, not only raw rows.
   - Show executed SQL statements at the end of the response.

## Known F1 Gotchas

Apply these defaults first when relevant:

- `drivers_championship.position` is TEXT. Filter using quoted values like `position = '1'`.
- `constructors_championship.position` is INTEGER. Filter using numeric values like `position = 1`.
- `race_wins.date` is TEXT in `DD Mon YYYY`; parse with `TO_DATE(date, 'DD Mon YYYY')`.

## Use References

- Read `references/f1-data-gotchas.md` for known table-specific issues.
- Read `references/dash-tools-usage.md` for expected tool usage and query-safety conventions.

## Use Script

- Run `scripts/check_query_safety.py` before executing uncertain SQL.
- Treat script `errors` as blockers and `warnings` as prompts to improve the query.
