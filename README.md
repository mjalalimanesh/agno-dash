# Self-Learning Data Agent

A self-learning data agent that provides **insights**, not just query results.

Inspired by [OpenAI's internal data agent](https://openai.com/index/how-openai-built-its-data-agent/) that serves 3.5k users across 600 PB of data. Their key insight:

> "Most Text-to-SQL failures are not 'model is dumb', they're 'model is missing context and tribal knowledge' issues."

This agent implements their solution: **6 layers of context** that transform text-to-SQL into a self-improving system.

## The 6 Layers of Context

| Layer | Purpose | Implementation |
|-------|---------|----------|
| **1. Table Metadata** | Schema, columns, types | `knowledge/tables/*.json` |
| **2. Human Annotations** | Business rules, gotchas | `knowledge/business/*.json` |
| **3. Query Patterns** | Validated SQL | `knowledge/queries/*.sql` |
| **4. Institutional Knowledge** | External context | MCP connectors (optional) |
| **5. Memory** | Corrections, preferences | Agno's `LearningMachine` |
| **6. Runtime Context** | Live schema inspection | `introspect_schema` tool |

**The magic**: Layers 1-4 provide static context. Layer 5 enables **continuous learning**. Layer 6 provides **fallback** when everything else fails.

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone and configure

```sh
git clone https://github.com/your-org/data-agent.git
cd data-agent

cp example.env .env
# Add your OPENAI_API_KEY to .env
```

### 2. Start the database

```sh
docker compose up -d
```

### 3. Load sample data and run

```sh
# Setup virtual environment
./scripts/venv_setup.sh
source .venv/bin/activate

# Load the F1 dataset
python -m da.scripts.load_dataset

# Run the agent
python -m da
```

## Usage

The agent is designed to provide insights, not just raw data:

```
> Who has won the most F1 World Championships?

I'll search the knowledge base and query the drivers championship data.

Based on the data, **Michael Schumacher** holds the record with **7 World Championships**,
followed by Lewis Hamilton with 7 (as of this dataset's cutoff in 2020).

Key insight: The dataset covers 1950-2020, so recent championships are not included.

Would you like to:
1. See the breakdown by decade?
2. Compare their career statistics?
3. Save this query for future use?
```

## Project Structure

```
data-agent/
├── da/                          # The Data Agent
│   ├── agent.py                 # Main agent with 6 layers
│   ├── config.py                # Configuration
│   ├── context/                 # Context builders
│   │   ├── semantic_model.py    # Layer 1: Table metadata
│   │   ├── business_rules.py    # Layer 2: Business context
│   │   └── query_patterns.py    # Layer 3: SQL patterns
│   ├── tools/                   # Agent tools
│   │   ├── analyze.py           # Result analysis
│   │   ├── introspect.py        # Layer 6: Runtime schema
│   │   └── save_query.py        # Save validated queries
│   └── evals/                   # Evaluation suite
│       ├── test_cases.py        # 18 test cases
│       └── run_evals.py         # Evaluation runner
├── knowledge/                   # Static knowledge (editable)
│   ├── tables/                  # Table metadata JSON
│   ├── business/                # Business rules JSON
│   └── queries/                 # Validated SQL patterns
├── datasets/                    # Sample datasets
│   └── f1/                      # Formula 1 data (1950-2020)
├── app/                         # Production deployment
├── db/                          # Database utilities
├── scripts/                     # Helper scripts
├── compose.yaml                 # Docker Compose
└── implementation.md            # Full specification
```

## How It Works

### The Learning Loop

```
User asks question
        │
        ▼
┌─────────────────────────────────────────┐
│   1. Search Knowledge Base (Layers 1-3) │
│      - Similar questions                │
│      - Validated patterns               │
│      - Data quality notes               │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│   2. Generate & Execute SQL             │
│      - Use context from semantic model  │
│      - Handle type mismatches           │
│      - Self-correct with Layer 6        │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│   3. Analyze & Explain                  │
│      - Key findings                     │
│      - Context and insights             │
│      - Follow-up suggestions            │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│   4. Learn & Improve                    │
│      - Offer to save query              │
│      - LearningMachine captures patterns│
│      - Future questions benefit         │
└─────────────────────────────────────────┘
```

### Data Quality Handling

The agent is designed to handle messy real-world data:

```
> Who won the World Championship in 2019?

⚠️ Note: The `position` column in `drivers_championship` is TEXT, not INTEGER.
Using string comparison: position = '1'

Result: Lewis Hamilton won the 2019 World Championship with 413 points.
```

## Evaluation

Run the test suite to verify agent performance:

```sh
# Run all tests
python -m da.evals.run_evals

# Run by category
python -m da.evals.run_evals --category data_quality

# Run by difficulty
python -m da.evals.run_evals --difficulty hard

# Show statistics
python -m da.evals.run_evals --stats
```

Categories: `basic`, `aggregation`, `data_quality`, `complex`, `edge_case`

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DATA_AGENT_MODEL` | No | `gpt-4.1` | Model to use |
| `DATA_AGENT_TEMPERATURE` | No | `0.0` | Model temperature |
| `DATA_AGENT_ENABLE_LEARNING` | No | `true` | Enable LearningMachine |
| `EXA_API_KEY` | No | - | Enables Layer 4 (MCP) |

### Pydantic Config

All settings are managed via Pydantic in `da/config.py`:

```python
DATA_AGENT_MODEL=gpt-4.1
DATA_AGENT_MAX_RESULTS=10
DATA_AGENT_DEFAULT_LIMIT=50
DATA_AGENT_ENABLE_LEARNING=true
```

## Add Your Own Data

### 1. Create table metadata

```json
// knowledge/tables/my_table.json
{
  "table_name": "users",
  "table_description": "User accounts",
  "table_columns": [
    {
      "name": "id",
      "type": "INTEGER",
      "description": "Primary key"
    },
    {
      "name": "email",
      "type": "TEXT",
      "description": "User email (always lowercase)"
    }
  ],
  "data_quality_notes": [
    "Email is always stored lowercase",
    "Some older records have NULL email"
  ]
}
```

### 2. Add business rules

```json
// knowledge/business/my_rules.json
{
  "metrics": [
    {
      "name": "Active User",
      "definition": "User with login in last 30 days",
      "table": "users",
      "calculation": "WHERE last_login > NOW() - INTERVAL '30 days'"
    }
  ],
  "common_gotchas": [
    {
      "issue": "Timezone handling",
      "tables_affected": ["users", "events"],
      "solution": "All timestamps are UTC"
    }
  ]
}
```

### 3. Load your data

```sh
# Load CSV/Parquet into the database
python -m da.scripts.load_dataset --path /path/to/data

# Rebuild knowledge base
python -m da.scripts.load_knowledge
```

## Development

```sh
# Setup
./scripts/venv_setup.sh
source .venv/bin/activate

# Format and lint
./scripts/format.sh
./scripts/validate.sh

# Run locally
python -m da

# Run with Docker
docker compose up -d --build
```

## Deploy to Production

### Railway

```sh
railway login
./scripts/railway_up.sh
```

### Docker

```sh
docker build -t data-agent .
docker run -p 8000:8000 --env-file .env data-agent
```

## References

- [OpenAI Data Agent Article](https://openai.com/index/how-openai-built-its-data-agent/)
- [Agno Framework](https://docs.agno.com)
- [Implementation Specification](implementation.md)

## License

MIT
