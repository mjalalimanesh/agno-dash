# Metabase MCP Integration Plan for Dash

## Summary

Add `mcp-metabase-server` as an additional MCP tool in Dash, running inside the `dash-api` container over stdio via `npx`. Keep Exa MCP unchanged. Enable Metabase MCP only when required environment variables are present, so deployments still succeed without Metabase.

## Scope

- Add Node.js runtime support in the API image so `npx` is available.
- Register Metabase MCP in `dash/agents.py` with conditional enablement.
- Pass Metabase env vars through local and production compose files.
- Document new env vars and deployment behavior.
- Add CI deploy logging that shows whether Metabase MCP env is configured.

## Decisions

- Runtime target: inside `dash-api` container.
- Auth mode: Metabase API key.
- Deploy policy: warn and continue if Metabase env vars are missing.
- Transport: `stdio` through `MCPTools(command=..., transport="stdio")`.

## Public Interface / Config Changes

New environment variables:

- `METABASE_URL` (required to enable Metabase MCP)
- `METABASE_API_KEY` (required to enable Metabase MCP)

Optional future fallback variables (not required for initial path):

- `METABASE_USERNAME`
- `METABASE_PASSWORD`

## Implementation Steps

1. Install Node.js/npm in `Dockerfile`.
2. Add conditional Metabase MCP tool registration in `dash/agents.py`.
3. Add env var passthrough in `compose.yaml` and `compose.prod.yaml`.
4. Add env examples in `example.env`.
5. Update docs: `README.md`, `deployment.md`, `AGENTS.md`, `CLAUDE.md`.
6. Add deploy-time env presence log in `.gitlab-ci.yml` (non-blocking).

## Runtime Behavior

- If both `METABASE_URL` and `METABASE_API_KEY` are set:
  - Dash loads Metabase MCP tools.
- If either is missing:
  - Dash logs a warning and starts normally without Metabase MCP.

## Validation Scenarios

1. Metabase vars set:
   - Container starts.
   - MCP tools initialize.
   - Metabase MCP calls succeed.
2. Metabase vars missing:
   - Container starts.
   - Warning appears in logs.
   - Agent remains functional.
3. Invalid key:
   - Agent starts.
   - Metabase tool calls fail with auth error only.
4. Regression:
   - Exa MCP still works.

## References

- https://github.com/easecloudio/mcp-metabase-server
- https://hub.docker.com/mcp/server/metabase/overview
