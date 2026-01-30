# CLAUDE.md

Project instructions for Claude Code when working with this repository.

## Project Overview

Data Agent - A self-learning data agent that provides insights, not just query results. Inspired by OpenAI's internal data agent.

## Architecture

The agent implements 6 layers of context:

```
da/                              # The Data Agent
├── agent.py                     # Main agent with all 6 layers
├── config.py                    # Pydantic configuration
├── context/                     # Context builders (Layers 1-3)
│   ├── semantic_model.py        # Layer 1: Table metadata
│   ├── business_rules.py        # Layer 2: Business rules
│   └── query_patterns.py        # Layer 3: Query patterns
├── tools/                       # Agent tools
│   ├── analyze.py               # Result analysis
│   ├── introspect.py            # Layer 6: Runtime schema
│   └── save_query.py            # Save validated queries
└── evals/                       # Evaluation suite

knowledge/                       # Static knowledge files
├── tables/                      # Table metadata (JSON)
├── business/                    # Business rules (JSON)
└── queries/                     # Validated SQL patterns
```

## Key Files

| File | Purpose |
|------|---------|
| `da/agent.py` | Main agent definition with 6 layers, LearningMachine |
| `da/config.py` | Pydantic settings with `DATA_AGENT_` prefix |
| `da/context/semantic_model.py` | Loads table metadata from knowledge/tables/ |
| `da/context/business_rules.py` | Loads business rules from knowledge/business/ |
| `da/context/query_patterns.py` | Loads SQL patterns from knowledge/queries/ |
| `knowledge/tables/*.json` | Table metadata with data quality notes |
| `knowledge/business/*.json` | Metrics, rules, common gotchas |
| `app/main.py` | Production deployment entry point |

## Development Setup

### Virtual Environment

```bash
./scripts/venv_setup.sh
source .venv/bin/activate
```

### Format & Validation

```bash
source .venv/bin/activate && ./scripts/format.sh
source .venv/bin/activate && ./scripts/validate.sh
```

### Run the Agent

```bash
# CLI mode
python -m da

# API server
python -m app.main
```

## The 6 Layers of Context

| Layer | Source | Code |
|-------|--------|------|
| 1. Table Metadata | `knowledge/tables/*.json` | `da/context/semantic_model.py` |
| 2. Human Annotations | `knowledge/business/*.json` | `da/context/business_rules.py` |
| 3. Query Patterns | `knowledge/queries/*.sql` | `da/context/query_patterns.py` |
| 4. Institutional Knowledge | MCP (optional) | Configured in `da/agent.py` |
| 5. Memory | LearningMachine | Configured in `da/agent.py` |
| 6. Runtime Context | `introspect_schema` tool | `da/tools/introspect.py` |

## Conventions

### Import Pattern

```python
# From da package
from da.agent import data_agent
from da.config import get_config
from da.context.semantic_model import SEMANTIC_MODEL_STR
from da.tools import analyze_results, introspect_schema

# From db utilities
from db import get_postgres_db, db_url
```

### Adding Knowledge

Table metadata goes in `knowledge/tables/`:
```json
{
  "table_name": "my_table",
  "table_description": "Description of the table",
  "table_columns": [
    {"name": "id", "type": "INTEGER", "description": "Primary key"}
  ],
  "data_quality_notes": ["Important notes about data quality"],
  "use_cases": ["What this table is used for"],
  "related_tables": ["other_table"]
}
```

Business rules go in `knowledge/business/`:
```json
{
  "metrics": [{"name": "Metric", "definition": "...", "table": "...", "calculation": "..."}],
  "business_rules": ["Rule 1", "Rule 2"],
  "common_gotchas": [{"issue": "...", "tables_affected": ["..."], "solution": "..."}]
}
```

### Configuration

All settings use Pydantic with `DATA_AGENT_` prefix:

```python
from da.config import get_config

config = get_config()
config.model           # DATA_AGENT_MODEL (default: gpt-4.1)
config.temperature     # DATA_AGENT_TEMPERATURE (default: 0.0)
config.max_results     # DATA_AGENT_MAX_RESULTS (default: 10)
config.default_limit   # DATA_AGENT_DEFAULT_LIMIT (default: 50)
config.enable_learning # DATA_AGENT_ENABLE_LEARNING (default: true)
```

## Commands

```bash
# Setup
./scripts/venv_setup.sh
source .venv/bin/activate

# Run agent (CLI)
python -m da

# Run agent (API)
python -m app.main

# Run evaluations
python -m da.evals.run_evals
python -m da.evals.run_evals --category basic
python -m da.evals.run_evals --stats

# Docker
docker compose up -d

# Format & validate
./scripts/format.sh
./scripts/validate.sh
```

## Data Quality Gotchas (F1 Dataset)

The F1 dataset has intentional data quality issues for testing:

| Issue | Tables | Solution |
|-------|--------|----------|
| `position` is TEXT | `drivers_championship` | Use `position = '1'` (string) |
| `position` is INTEGER | `constructors_championship` | Use `position = 1` (number) |
| `position` has special values | `race_results` | Can be 'Ret', 'DSQ', 'DNS', 'NC' |
| `date` is TEXT | `race_wins` | Use `TO_DATE(date, 'DD Mon YYYY')` |
| Column name varies | All | `name_tag` vs `driver_tag` |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_USER` | No | `ai` | Database user |
| `DB_PASS` | No | `ai` | Database password |
| `DB_DATABASE` | No | `ai` | Database name |
| `DATA_AGENT_MODEL` | No | `gpt-4.1` | Model to use |
| `DATA_AGENT_TEMPERATURE` | No | `0.0` | Model temperature |
| `DATA_AGENT_ENABLE_LEARNING` | No | `true` | Enable LearningMachine |
| `EXA_API_KEY` | No | - | Enables MCP (Layer 4) |

## Ports

- API: 8000
- Database: 5432

## Testing

The evaluation suite tests the agent across categories:
- `basic`: Simple queries
- `aggregation`: GROUP BY, COUNT
- `data_quality`: Type handling, gotchas
- `complex`: Multi-table queries
- `edge_case`: NULLs, errors

```bash
python -m da.evals.run_evals --stats
python -m da.evals.run_evals --category data_quality
python -m da.evals.run_evals --difficulty hard
```

---

## Agno Framework Reference

### Agent with LearningMachine

```python
from agno.agent import Agent
from agno.learn import LearningMachine, LearningMode
from agno.learn import UserProfileConfig, UserMemoryConfig, LearnedKnowledgeConfig

agent = Agent(
    id="my-agent",
    model=OpenAIResponses(id="gpt-4.1"),
    knowledge=my_knowledge,
    learning=LearningMachine(
        knowledge=my_knowledge,
        user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
        user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
)
```

### Knowledge Base Setup

```python
from agno.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

knowledge = Knowledge(
    name="My Knowledge",
    vector_db=PgVector(
        db_url=db_url,
        table_name="my_vectors",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    contents_db=get_postgres_db(contents_table="my_contents"),
)
```

### Custom Tools

```python
from agno.tools import tool

@tool
def my_tool(param: str) -> str:
    """Description of what this tool does.

    Args:
        param: Description of parameter.

    Returns:
        Description of return value.
    """
    return f"Result: {param}"
```

### Documentation Links

- https://docs.agno.com/llms.txt - Concise Agno overview
- https://docs.agno.com/llms-full.txt - Complete documentation
- https://docs.agno.com/knowledge - Knowledge & RAG
- https://docs.agno.com/agents/memory - Memory systems
