# Safe Interactive Metabase Embeds (Dash + Agent UI) -- v1 Plan

## Summary

Implement secure, interactive Metabase chart embedding for chat responses with these locked decisions:

1. Embedding mode: Signed guest embedding.
2. Scope: Question (card) embeds only in v1.
3. UI contract: Typed embed payload (not markdown iframe parsing).
4. Expiry behavior: Auto-refresh signed URL.
5. Network reality: Metabase is reachable only on company VPN, so interactive embeds are available only to VPN users.

## Public Interface and Type Changes

1. Add Dash server env vars in `example.env` and docs:
- `METABASE_EMBED_SECRET` (required for signed embeds)
- `METABASE_SITE_URL` (optional; defaults to `METABASE_URL`)
- `METABASE_EMBED_TTL_SECONDS` (default `900`)
- `METABASE_ALLOWED_QUESTION_IDS` (optional allowlist, comma-separated; recommended for high-sensitivity deployments)

2. Add new typed embed schema to Agent UI in `src/types/os.ts`:
- `MetabaseEmbedData { kind: "metabase_question", question_id: number, iframe_url: string, expires_at: number, title?: string, open_url?: string }`
- `AgentExtraData.embeds?: MetabaseEmbedData[]`
- `ChatMessage.extra_data.embeds?: MetabaseEmbedData[]`

3. Add backend endpoint for refresh in `app/main.py`:
- `POST /api/metabase/embed/refresh`
- Request: `{ "question_id": number }`
- Response: `{ "iframe_url": string, "expires_at": number }`
- Auth: same AgentOS auth model; reject unauthenticated calls.

4. Add Dash tool API in `dash/tools/metabase_embed.py`:
- `create_metabase_question_embed(question_id: int, title: str | None = None) -> dict`
- Returns typed payload matching `MetabaseEmbedData`.

## Implementation Steps

### 1. Dash backend signing and safety

1. Create `dash/tools/metabase_embed.py` with:
- JWT signing for guest embed token using `METABASE_EMBED_SECRET`.
- Payload restricted to `resource: { question: <id> }`, `params: {}`, `exp`.
- Validation: positive integer IDs only.
- Optional allowlist enforcement via `METABASE_ALLOWED_QUESTION_IDS`.
- Return both `iframe_url` and `open_url` for fallback.

2. Export tool in `dash/tools/__init__.py`.

3. Register tool in `dash/agent.py`:
- Add to `dash_tools` only when `METABASE_EMBED_SECRET` and Metabase MCP are enabled.
- Add explicit instructions: when user requests visualization, use `metabase_*` creation flow, then call `create_metabase_question_embed`, and include result in `extra_data.embeds`.

4. Add refresh endpoint in `app/main.py`:
- Server-only signing path for renewing expired URLs.
- Return `401/403` for unauthorized, `400` for invalid IDs, `503` when embedding disabled.

5. Update docs/config examples in:
- `README.md`
- `deployment.md`
- `example.env`
- `AGENTS.md` (if needed for operator workflow)

### 2. Agent UI interactive renderer

1. Add embed renderer component:
- `src/components/chat/ChatArea/Messages/Multimedia/Embeds/MetabaseEmbeds.tsx`
- Render secure `<iframe>` with fixed aspect ratio and loading state.
- Show "Open in Metabase" fallback link.

2. Wire renderer into message UI:
- `src/components/chat/ChatArea/Messages/MessageItem.tsx`
- Render embeds from `message.extra_data?.embeds`.

3. Extend stream handling:
- `src/hooks/useAIStreamHandler.tsx`
- Preserve and merge `chunk.extra_data.embeds` across streaming chunks and completion.

4. Extend session rehydration:
- `src/hooks/useSessionLoader.tsx`
- Load historical `extra_data.embeds` into `ChatMessage`.

5. Add auto-refresh logic in renderer:
- If `expires_at` is near/elapsed, call `POST /api/metabase/embed/refresh` through AgentOS base URL.
- Replace iframe URL in local component state without requiring a new user prompt.

### 3. Frontend hardening for iframe security

1. Add strict CSP in `next.config.ts`:
- `frame-src` allow only configured Metabase origin.
- Restrict `connect-src`/`img-src` as needed for existing app behavior.

2. Add referrer policy and iframe attributes:
- `referrerPolicy="no-referrer"`
- `sandbox` with minimum required capabilities for Metabase embeds.
- `allow` only required features.

3. Add environment/config for allowed Metabase origin in UI runtime config.

### 4. Operational safeguards

1. Use dedicated least-privilege Metabase account for MCP key.
2. Never log embed JWT or full signed URL.
3. Default TTL to 900s; reject TTL > safe cap (e.g., 3600s).
4. Return generic errors to UI; keep detailed errors server-side.
5. Document VPN prerequisite clearly for end users.

## Test Cases and Scenarios

### Dash tests

1. Unit: signer creates valid URL for `question_id`.
2. Unit: missing `METABASE_EMBED_SECRET` disables signing tool.
3. Unit: invalid ID and non-allowlisted ID are rejected.
4. Unit: TTL bounds enforced.
5. API: refresh endpoint returns new URL with later `expires_at`.
6. API: unauthorized request rejected.
7. Integration: MCP-created question ID -> signed embed payload shape matches UI type.

### Agent UI tests

1. Component: renders iframe when `extra_data.embeds` exists.
2. Component: expired embed triggers refresh call and iframe URL update.
3. Component: refresh failure shows fallback link and retry affordance.
4. Stream handler: preserves `extra_data.embeds` during `RunContent` and `RunCompleted`.
5. Session loader: historical chats with embeds re-render correctly.
6. CSP regression: no break to existing images/videos/audio rendering paths.

### End-to-end scenarios

1. User asks "create a chart of X" -> agent creates Metabase question -> chat shows interactive iframe.
2. Token expires during session -> auto-refresh succeeds silently.
3. User off VPN -> iframe fails gracefully with actionable "connect to VPN" message and fallback link.
4. No embedding secret configured -> agent returns non-interactive link with explicit reason.

## Acceptance Criteria

1. Interactive question embeds appear in `agent-ui` without exposing secrets client-side.
2. Expired tokens auto-refresh without user prompt in normal conditions.
3. Unsafe modes (public links) are not used by default.
4. MCP and embed signing remain separated: API key for MCP, embed secret for JWT.
5. Non-VPN users get a clear graceful fallback, not broken blank UI.

## Assumptions and Defaults

1. Metabase embedding feature is enabled in Metabase admin.
2. Organization accepts VPN-only availability for interactive embeds in v1.
3. v1 supports `question` resource only; dashboards deferred.
4. Default TTL is 900 seconds.
5. `extra_data.embeds` is the canonical transport contract (not markdown parsing, not new top-level run field).
