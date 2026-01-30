# Data Agent

A self-learning data agent inspired by [OpenAI's internal data agent](https://openai.com/index/how-openai-built-its-data-agent/).

## The Key Insight

OpenAI's data agent serves 3.5k users across 70k datasets. Their key finding:

> "Most Text-to-SQL failures are not 'model is dumb', they're 'model is missing context and tribal knowledge' issues."

This agent implements their **6 layers of context** approach, transforming a basic text-to-SQL tool into a system that learns and improves with every interaction.

## Quick Start

```bash
# 1. Start PostgreSQL
docker compose up -d

# 2. Load sample data (Formula 1 1950-2020)
python -m data_agent.scripts.load_data

# 3. Load knowledge base
python -m data_agent.scripts.load_knowledge

# 4. Run the agent
python -m data_agent
```

## The 6 Layers of Context

| Layer | Purpose | Location |
|-------|---------|----------|
| **1. Table Metadata** | Schema, columns, types | `knowledge/tables/` |
| **2. Human Annotations** | Business rules, caveats | `knowledge/business/` |
| **3. Query Patterns** | Validated SQL that works | `knowledge/queries/` |
| **4. Institutional Knowledge** | External docs via MCP | Optional (Exa) |
| **5. Memory** | Corrections, preferences | `LearningMachine` |
| **6. Runtime Context** | Live schema inspection | `introspect_schema` |

**The magic**: Layers 1-4 provide static context. Layer 5 enables **continuous learning**. Layer 6 provides **runtime fallback**.

## Example Queries

```
> Who won the most races in 2019?
Lewis Hamilton won the most races in 2019 with 11 wins.

> Which driver has won the most world championships?
Michael Schumacher with 7 championships, followed by Lewis Hamilton with 7.

> Compare Ferrari vs Mercedes from 2015-2020
[Detailed comparison with insights]
```

## Architecture

```
data_agent/
├── agent.py              # Main agent with LearningMachine
├── config.py             # Configuration management
├── context/              # Context builders (Layers 1-3)
│   ├── semantic_model.py # Table metadata
│   ├── business_rules.py # Business definitions
│   └── query_patterns.py # SQL patterns
├── tools/                # Agent tools
│   ├── analyze.py        # Result analysis
│   ├── save_query.py     # Query saving (learning loop)
│   └── introspect.py     # Runtime schema (Layer 6)
├── knowledge/            # Static knowledge files
│   ├── tables/           # Table JSON files
│   ├── queries/          # Validated SQL
│   └── business/         # Business rules
├── evals/                # Evaluation suite
└── scripts/              # Setup utilities
```

## How It Works

### The Learning Loop

```
User Question
    │
    ▼
┌───────────────────┐
│ Search Knowledge  │ ◄── Layers 1-3: Static context
│ Base First        │
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Generate SQL      │ ◄── With data quality notes
│ with Context      │
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Execute & Analyze │ ◄── Provide insights, not just data
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Offer to Save     │ ◄── Learning loop: save for future
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Learn from        │ ◄── Layer 5: LearningMachine
│ Corrections       │
└───────────────────┘
```

### Key Behaviors

1. **Search First**: Always queries knowledge base before generating SQL
2. **Data Quality Aware**: Follows documented type mismatches and formats
3. **Insights Over Data**: Provides analysis, not just raw results
4. **Self-Improving**: Saves successful queries and learns from corrections

## Configuration

All settings via environment variables:

```bash
# Model
DATA_AGENT_MODEL=gpt-4.1      # Default model
DATA_AGENT_TEMPERATURE=0.0    # Model temperature

# Behavior
DATA_AGENT_SEARCH_KNOWLEDGE=true   # Always search KB first
DATA_AGENT_ENABLE_LEARNING=true    # Enable LearningMachine
DATA_AGENT_DEFAULT_LIMIT=50        # Default SQL LIMIT

# Database (optional - defaults work with docker-compose)
DB_HOST=localhost
DB_PORT=5432
DB_USER=ai
DB_PASS=ai
DB_DATABASE=ai

# Optional APIs
EXA_API_KEY=...   # Enables web research (Layer 4)
```

## Evaluation

Run the test suite:

```bash
# All tests
python -m data_agent.evals.run_evals

# By category
python -m data_agent.evals.run_evals --category basic
python -m data_agent.evals.run_evals --category data_quality

# By difficulty
python -m data_agent.evals.run_evals --difficulty easy

# Show statistics
python -m data_agent.evals.run_evals --stats

# JSON output (for CI)
python -m data_agent.evals.run_evals --json
```

Categories:
- `basic`: Simple queries
- `aggregation`: GROUP BY, COUNT
- `data_quality`: Type mismatch handling (the hard ones!)
- `complex`: Multi-table queries
- `edge_case`: Special values, NULLs

## Adding Your Own Data

### 1. Create Table Metadata

Add `knowledge/tables/your_table.json`:

```json
{
  "table_name": "your_table",
  "table_description": "What this table contains",
  "use_cases": ["Example query 1", "Example query 2"],
  "data_quality_notes": [
    "Important note about data types",
    "Gotchas to watch out for"
  ],
  "table_columns": [
    {
      "name": "column_name",
      "type": "text",
      "description": "What this column contains"
    }
  ]
}
```

### 2. Add Business Rules

Add `knowledge/business/your_rules.json`:

```json
{
  "metrics": [
    {
      "name": "Your Metric",
      "definition": "What it means",
      "table": "your_table",
      "calculation": "How to calculate it"
    }
  ],
  "business_rules": [
    "Important domain rule 1",
    "Important domain rule 2"
  ],
  "common_gotchas": [
    {
      "issue": "Common mistake",
      "tables_affected": ["your_table"],
      "solution": "How to fix it"
    }
  ]
}
```

### 3. Load Your Data

```bash
# Load data into PostgreSQL
python -c "
import pandas as pd
from sqlalchemy import create_engine
engine = create_engine('postgresql+psycopg://ai:ai@localhost:5432/ai')
df = pd.read_csv('your_data.csv')
df.to_sql('your_table', engine, if_exists='replace', index=False)
"

# Reload knowledge base
python -m data_agent.scripts.load_knowledge
```

## Why This Approach Works

Traditional text-to-SQL fails because:
- Models don't know about data type inconsistencies
- They miss business context ("championship started in 1958")
- They can't learn from past mistakes

This agent succeeds because:
- **Explicit context**: Every data quirk is documented
- **Search-first**: Reuses validated patterns
- **Learning loop**: Improves with every correction
- **Runtime fallback**: Can inspect live schema when stuck

## References

- [OpenAI Data Agent Article](https://openai.com/index/how-openai-built-its-data-agent/)
- [Agno Framework](https://docs.agno.com)
- [LearningMachine Documentation](https://docs.agno.com/agents/learning)
