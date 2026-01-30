"""
Data Agent
==========

A self-learning data agent inspired by OpenAI's internal data agent.

The agent uses TWO types of knowledge bases:

1. KNOWLEDGE (static, curated):
   - Table metadata and schemas
   - Validated SQL query patterns
   - Business rules and definitions
   → Search this FIRST for table info, query patterns, data quality notes

2. LEARNINGS (dynamic, discovered):
   - Patterns discovered through interaction
   - Query fixes and corrections
   - Type gotchas and workarounds
   → Search this when queries fail or to avoid past mistakes
   → Save here when discovering new patterns

The 6 Layers of Context:
1. Table Metadata - Schema info from knowledge/tables/
2. Human Annotations - Business rules from knowledge/business/
3. Query Patterns - Validated SQL from knowledge/queries/
4. Institutional Knowledge - External context via MCP (optional)
5. Learnings - Discovered patterns (separate from knowledge)
6. Runtime Context - Live schema inspection via introspect_schema tool
"""

from os import getenv

from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIResponses
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.sql import SQLTools
from agno.vectordb.pgvector import PgVector, SearchType

from da.context.business_rules import BUSINESS_CONTEXT
from da.context.semantic_model import SEMANTIC_MODEL_STR
from da.tools import (
    create_introspect_schema_tool,
    create_learnings_tools,
    create_save_validated_query_tool,
)
from db import db_url, get_postgres_db

# ============================================================================
# Database & Knowledge Bases
# ============================================================================

# Database for storing agent sessions
agent_db = get_postgres_db()

# KNOWLEDGE: Static, curated information (table schemas, validated queries, business rules)
data_agent_knowledge = Knowledge(
    name="Data Agent Knowledge",
    vector_db=PgVector(
        db_url=db_url,
        table_name="data_agent_knowledge",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    contents_db=get_postgres_db(contents_table="data_agent_knowledge_contents"),
    max_results=10,
)

# LEARNINGS: Dynamic, discovered patterns (query fixes, corrections, gotchas)
data_agent_learnings = Knowledge(
    name="Data Agent Learnings",
    vector_db=PgVector(
        db_url=db_url,
        table_name="data_agent_learnings",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    contents_db=get_postgres_db(contents_table="data_agent_learnings_contents"),
    max_results=5,
)

# ============================================================================
# Create Tools
# ============================================================================

# Knowledge tools (save validated queries)
save_validated_query = create_save_validated_query_tool(data_agent_knowledge)

# Learnings tools (search/save discovered patterns)
search_learnings, save_learning = create_learnings_tools(data_agent_learnings)

# Runtime schema inspection (Layer 6)
introspect_schema = create_introspect_schema_tool(db_url)

# ============================================================================
# Instructions
# ============================================================================

INSTRUCTIONS = f"""\
You are a Data Agent that provides **insights**, not just query results.

## Two Storage Systems

**Knowledge** (static, curated):
- Table schemas, validated queries, business rules
- Searched automatically before each response
- Add successful queries here with `save_validated_query`

**Learnings** (dynamic, discovered):
- Patterns YOU discover through errors and fixes
- Type gotchas, date formats, column quirks
- Search with `search_learnings`, save with `save_learning`

## CRITICAL: What goes where

| Situation | Action |
|-----------|--------|
| Before writing SQL | `search_learnings("table_name column types")` |
| Query fails with type error | Fix it, then `save_learning` |
| Query works and is reusable | Offer `save_validated_query` |
| Need actual column types | `introspect_schema(table_name="...")` |

## When to call search_learnings

BEFORE writing any SQL, search for gotchas:
```
search_learnings("race_wins date column")
search_learnings("drivers_championship position type")
```

## When to call save_learning

1. **After fixing a type error**
```
save_learning(
  title="drivers_championship position is TEXT",
  learning="Use position = '1' not position = 1",
  context="Column is TEXT despite storing numbers",
  tags=["type", "drivers_championship"]
)
```

2. **After discovering a date format**
```
save_learning(
  title="race_wins date parsing",
  learning="Use TO_DATE(date, 'DD Mon YYYY') to extract year",
  context="Date stored as text like '15 Mar 2019'",
  tags=["date", "race_wins"]
)
```

3. **After a user corrects you**
```
save_learning(
  title="Constructors Championship started 1958",
  learning="No constructors data before 1958 - query will return empty",
  context="User pointed out the championship didn't exist before then",
  tags=["business", "constructors_championship"]
)
```

## Workflow: Answering a question

1. `search_learnings` for relevant gotchas
2. Write SQL (LIMIT 50, no SELECT *, ORDER BY for rankings)
3. If error → `introspect_schema` → fix → `save_learning`
4. Provide **insights**, not just data:
   - "Hamilton won 11 of 21 races (52%)"
   - "7 more than second place Bottas"
   - "His most dominant since 2015"
5. Offer to save if query is reusable

## SQL Rules

- LIMIT 50 by default
- Never SELECT * - specify columns
- ORDER BY for top-N queries
- No DROP, DELETE, UPDATE, INSERT

## Personality

- Insightful, not just accurate
- Learns from every mistake
- Never repeats the same error twice

---

## SEMANTIC MODEL

{SEMANTIC_MODEL_STR}

---

{BUSINESS_CONTEXT}
"""

# ============================================================================
# Build Tools List
# ============================================================================

tools: list = [
    # SQL execution
    SQLTools(db_url=db_url),
    # Reasoning
    ReasoningTools(add_instructions=True),
    # Knowledge tools
    save_validated_query,
    # Learnings tools
    search_learnings,
    save_learning,
    # Runtime introspection (Layer 6)
    introspect_schema,
    # MCP tools for external knowledge (Layer 4)
    MCPTools(url=f"https://mcp.exa.ai/mcp?exaApiKey={getenv('EXA_API_KEY', '')}&tools=web_search_exa"),
]

# ============================================================================
# Create Agent
# ============================================================================

data_agent = Agent(
    id="data-agent",
    name="Data Agent",
    model=OpenAIResponses(id="gpt-5.2"),
    db=agent_db,
    # Knowledge (static - table schemas, validated queries)
    knowledge=data_agent_knowledge,
    search_knowledge=True,
    instructions=INSTRUCTIONS,
    tools=tools,
    # Context settings
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    read_tool_call_history=True,
    # Memory (user preferences)
    enable_agentic_memory=True,
    # Output
    markdown=True,
)

# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    # Test queries to verify the agent works
    test_queries = [
        "Who won the most races in 2019?",
        "Which driver has won the most World Championships?",
    ]

    for query in test_queries:
        data_agent.print_response(query, stream=True)
