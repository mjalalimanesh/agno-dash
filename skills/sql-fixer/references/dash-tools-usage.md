# Dash Tools Usage

Use these tool patterns when fixing SQL errors in Dash.

## Retrieval Before SQL

1. `search_knowledge_base` for validated patterns and known table usage.
2. `search_learnings` for prior fixes and data quirks.

## Query and Debug Loop

1. Run SQL with the analytics SQL tools.
2. If there is an error, call `introspect_schema` for exact column and type info.
3. Adjust SQL and retry.
4. Save durable fixes with `save_learning`.

## Save Reusable Success

- Use `save_validated_query` when:
  - SQL executes correctly.
  - It captures a pattern likely to be reused.
  - It follows read-only and formatting rules.

## Query Quality Checks

- Read-only SQL only.
- Prefer explicit columns over `SELECT *`.
- Add `ORDER BY` for ranking output.
- Add `LIMIT 50` by default.
- Keep SQL scoped to one database per query.
