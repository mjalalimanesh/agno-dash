"""
Dash - Self-learning data agent
===============================

Test: python -m dash.agent
"""

from os import getenv
from pathlib import Path

from agno.agent import Agent
from agno.learn import (
    LearnedKnowledgeConfig,
    LearningMachine,
    LearningMode,
)
from agno.models.openrouter import OpenRouter
from agno.skills import LocalSkills, Skills
from agno.tools.mcp import MCPTools

from dash.context.business_rules import BUSINESS_CONTEXT
from dash.context.semantic_model import SEMANTIC_MODEL_STR
from dash.tools import (
    create_analytics_sql_tools,
    create_introspect_schema_tool,
    create_save_validated_query_tool,
)
from db import create_knowledge, get_analytics_descriptions, get_analytics_registry, get_postgres_db

OPENROUTER_API_KEY = getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _env_bool(name: str, default: bool) -> bool:
    """Parse common truthy/falsy env values with a default fallback."""
    raw = getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_dash_skills() -> Skills | None:
    """Load skills from the local skills directory, fail-open on any issue."""
    if not _env_bool("DASH_SKILLS_ENABLED", True):
        print("INFO: Skills are disabled via DASH_SKILLS_ENABLED.")
        return None

    skills_dir_raw = getenv("DASH_SKILLS_DIR", "skills").strip() or "skills"
    skills_dir = Path(skills_dir_raw)
    if not skills_dir.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        skills_dir = repo_root / skills_dir

    validate_skills = _env_bool("DASH_SKILLS_VALIDATE", True)

    if not skills_dir.exists():
        print(
            f"WARNING: Skills directory not found at '{skills_dir}'. "
            "Continuing without skills."
        )
        return None

    try:
        loaded_skills = Skills(
            loaders=[
                LocalSkills(path=str(skills_dir), validate=validate_skills),
            ]
        )
        skill_names = loaded_skills.get_skill_names()
        if not skill_names:
            print(
                f"WARNING: No skills discovered in '{skills_dir}'. "
                "Continuing without skills."
            )
            return None

        print(
            f"INFO: Loaded {len(skill_names)} skill(s) from '{skills_dir}': "
            f"{', '.join(skill_names)}"
        )
        return loaded_skills
    except Exception as exc:
        print(
            f"WARNING: Failed to load skills from '{skills_dir}' "
            f"(validate={validate_skills}): {exc}. Continuing without skills."
        )
        return None

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

agent_db = get_postgres_db()
dash_skills = load_dash_skills()

# Dual knowledge system
# KNOWLEDGE: Static, curated (table schemas, validated queries, business rules)
dash_knowledge = create_knowledge(
    name="Dash Knowledge",
    table_name="dash_knowledge",
    embedder_id="openai/text-embedding-3-small",
    embedder_api_key=OPENROUTER_API_KEY,
    embedder_base_url=OPENROUTER_BASE_URL,
)

# LEARNINGS: Dynamic, discovered (error patterns, gotchas, user corrections)
dash_learnings = create_knowledge(
    name="Dash Learnings",
    table_name="dash_learnings",
    embedder_id="openai/text-embedding-3-small",
    embedder_api_key=OPENROUTER_API_KEY,
    embedder_base_url=OPENROUTER_BASE_URL,
)

# ============================================================================
# Analytics DB registry (read-only; used by SQL and introspect tools)
# ============================================================================

analytics_registry = get_analytics_registry()
analytics_descriptions = get_analytics_descriptions()

# ============================================================================
# Tools
# ============================================================================

save_validated_query = create_save_validated_query_tool(dash_knowledge)
analytics_tools = create_analytics_sql_tools(analytics_registry)
introspect_schema = create_introspect_schema_tool(analytics_registry)

dash_tools: list = [
    *analytics_tools,
    save_validated_query,
    introspect_schema,
    MCPTools(
        url=(
            "https://mcp.exa.ai/mcp"
            f"?exaApiKey={getenv('EXA_API_KEY', '')}&tools=web_search_exa"
        )
    ),
]

metabase_url = getenv("METABASE_URL", "").strip()
metabase_api_key = getenv("METABASE_API_KEY", "").strip()
metabase_username = getenv("METABASE_USERNAME", "").strip()
metabase_password = getenv("METABASE_PASSWORD", "").strip()
npm_config_cache = getenv("NPM_CONFIG_CACHE", "/tmp/.npm").strip()

metabase_env: dict[str, str] = {}
if metabase_url:
    metabase_env["METABASE_URL"] = metabase_url
if metabase_api_key:
    metabase_env["METABASE_API_KEY"] = metabase_api_key
if metabase_username:
    metabase_env["METABASE_USERNAME"] = metabase_username
if metabase_password:
    metabase_env["METABASE_PASSWORD"] = metabase_password
if npm_config_cache:
    metabase_env["NPM_CONFIG_CACHE"] = npm_config_cache

has_api_key_auth = bool(metabase_url and metabase_api_key)
has_user_pass_auth = bool(metabase_url and metabase_username and metabase_password)

if has_api_key_auth or has_user_pass_auth:
    dash_tools.append(
        MCPTools(
            command="npx -y @easecloudio/mcp-metabase-server",
            transport="stdio",
            env=metabase_env,
            tool_name_prefix="metabase_",
            timeout_seconds=60,
        )
    )
else:
    print(
        "WARNING: Metabase MCP tool is disabled. "
        "Set METABASE_URL with METABASE_API_KEY "
        "(or METABASE_USERNAME + METABASE_PASSWORD)."
    )

# ============================================================================
# Instructions
# ============================================================================


def _build_databases_section(
    registry: dict[str, str], descriptions: dict[str, str]
) -> str:
    """Build AVAILABLE DATABASES section for agent instructions."""
    lines = ["## AVAILABLE DATABASES\n"]
    lines.append(
        "These are the analytics databases you can query (read-only):\n"
    )
    for name in sorted(registry):
        desc = descriptions.get(name, "")
        lines.append(f"- **{name}**" + (f": {desc}" if desc else ""))
    lines.append("\nRules:")
    lines.append(
        "- These databases are read-only. Never attempt INSERT/UPDATE/DELETE"
    )
    lines.append("- Never mix databases in a single query (no cross-DB joins)")
    if len(registry) > 1:
        lines.append(
            "- Always pass `database` to list_tables, describe_table, "
            "run_sql_query, introspect_schema"
        )
        lines.append("- Choose the database based on the user's question")
        lines.append("- If unclear, ask the user which database to use")
    return "\n".join(lines)


DATABASES_SECTION = _build_databases_section(
    analytics_registry, analytics_descriptions
)

INSTRUCTIONS = f"""\
You are Dash, a self-learning data agent that provides **insights**, not just query results.

## Your Purpose

You are the user's data analyst — one that never forgets, never repeats mistakes,
and gets smarter with every query.

You don't just fetch data. You interpret it, contextualize it, and explain what it means.
You remember the gotchas, the type mismatches, the date formats that tripped you up before.

Your goal: make the user look like they've been working with this data for years.

## Two Knowledge Systems

**Knowledge** (static, curated):
- Table schemas, validated queries, business rules
- Searched automatically before each response
- Add successful queries here with `save_validated_query`

**Learnings** (dynamic, discovered):
- Patterns YOU discover through errors and fixes
- Type gotchas, date formats, column quirks
- Search with `search_learnings`, save with `save_learning`

## Workflow

1. Always start with `search_knowledge_base` and `search_learnings` for table info, patterns, gotchas. Context that will help you write the best possible SQL.
2. Write SQL (LIMIT 50, no SELECT *, ORDER BY for rankings)
3. If error → `introspect_schema` → fix → `save_learning`
4. Provide **insights**, not just data, based on the context you found.
5. Offer `save_validated_query` if the query is reusable.

## When to save_learning

After fixing a type error:
```
save_learning(
  title="drivers_championship position is TEXT",
  learning="Use position = '1' not position = 1"
)
```

After discovering a date format:
```
save_learning(
  title="race_wins date parsing",
  learning="Use TO_DATE(date, 'DD Mon YYYY') to extract year"
)
```

After a user corrects you:
```
save_learning(
  title="Constructors Championship started 1958",
  learning="No constructors data before 1958"
)
```

## Insights, Not Just Data

| Bad | Good |
|-----|------|
| "Hamilton: 11 wins" | "Hamilton won 11 of 21 races (52%) — 7 more than Bottas" |
| "Schumacher: 7 titles" | "Schumacher's 7 titles stood for 15 years until Hamilton matched it" |

## SQL Rules

- LIMIT 50 by default
- Never SELECT * — specify columns
- ORDER BY for top-N queries
- No DROP, DELETE, UPDATE, INSERT

## Response Notes
- When ran queries Show All your ran SQL Queries In the End of your reponse with proper format.

---

{DATABASES_SECTION}

---

## SEMANTIC MODEL

{SEMANTIC_MODEL_STR}
---

{BUSINESS_CONTEXT}\
"""

# ============================================================================
# Create Agent
# ============================================================================

dash = Agent(
    id="dash",
    name="Dash",
    model=OpenRouter(
        id=getenv("DASH_MODEL", "openai/gpt-4o"),
        default_headers={
            "HTTP-Referer": "https://github.com/mjalalimanesh/agno-dash",
            "X-Title": "zp-agno-dash",
        },
    ),
    db=agent_db,
    instructions=INSTRUCTIONS,
    # Knowledge (static)
    knowledge=dash_knowledge,
    search_knowledge=True,
    # Skills (fail-open loader)
    skills=dash_skills,
    # Learning (provides search_learnings, save_learning)
    enable_agentic_memory=True,
    learning=LearningMachine(
        knowledge=dash_learnings,
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
    tools=dash_tools,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)

if __name__ == "__main__":
    dash.print_response("Who won the most races in 2019?", stream=True)
