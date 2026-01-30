# Data Agent: Implementation Specification

> **Goal**: Build the best open-source data agent on the planet, inspired by [OpenAI's internal data agent](https://openai.com/index/how-openai-built-its-data-agent/).

---

## Why This Matters

OpenAI's data agent serves 3.5k internal users across 600 PB of data in 70k datasets. Their key insight:

> "Most Text-to-SQL failures are not 'model is dumb', they're 'model is missing context and tribal knowledge' issues."

This repo implements their approach: **6 layers of context** that transform a simple text-to-SQL agent into a self-learning system that improves with every interaction.

---

## The 6 Layers of Context

| Layer | Purpose | Implementation |
|:------|:--------|:---------------|
| **1. Table Metadata** | Schema, columns, types, relationships | `knowledge/tables/*.yaml` |
| **2. Human Annotations** | Business meaning, caveats, gotchas | `data_quality_notes` + `knowledge/business/` |
| **3. Query Patterns** | Validated SQL that works | `knowledge/queries/*.sql` |
| **4. Institutional Knowledge** | Company context, docs, tribal knowledge | MCP connectors (optional) |
| **5. Memory** | Corrections, preferences, learned patterns | Agno's `LearningMachine` |
| **6. Runtime Context** | Live schema when KB is stale | `introspect_schema` tool |

**The magic**: Layers 1-4 provide static context. Layer 5 enables **continuous learning** from corrections. Layer 6 provides **fallback** when everything else fails.

---

## Architecture

```
da/                          # The Data Agent
├── __init__.py              # Package exports
├── __main__.py              # CLI entry point
├── agent.py                 # Main agent definition
├── config.py                # Configuration management
│
├── context/                 # The 6 Layers of Context
│   ├── __init__.py
│   ├── semantic_model.py    # Layer 1: Table metadata builder
│   ├── business_rules.py    # Layer 2: Business definitions
│   └── query_patterns.py    # Layer 3: SQL pattern loader
│
├── tools/                   # Agent tools
│   ├── __init__.py
│   ├── analyze.py           # Result analysis and insights
│   ├── save_query.py        # Save validated queries to KB
│   └── introspect.py        # Layer 6: Runtime schema inspection
│
├── scripts/                 # Utility scripts
│   ├── load_data.py         # Load dataset into database
│   └── load_knowledge.py    # Populate knowledge base
│
└── evals/                   # Evaluation suite
    ├── __init__.py
    ├── test_cases.py        # Test definitions (18 cases)
    └── run_evals.py         # Evaluation runner

knowledge/                   # Static knowledge (top-level)
├── tables/                  # Table metadata (JSON)
├── queries/                 # Validated SQL patterns
└── business/                # Business definitions

datasets/                    # Sample datasets
└── f1/                      # Formula 1 data (1950-2020)
```

---

## Core Components

### 1. The Agent (`agent.py`)

The heart of the system. Combines all 6 layers with Agno's LearningMachine.

```python
from agno.agent import Agent
from agno.learn import LearningMachine, LearningMode
from agno.tools.sql import SQLTools
from agno.tools.reasoning import ReasoningTools

data_agent = Agent(
    id="data-agent",
    name="Data Agent",
    model=OpenAIResponses(id="gpt-4.1"),

    # Knowledge base (Layers 1-3)
    knowledge=data_agent_knowledge,
    search_knowledge=True,  # CRITICAL: Always search before generating

    # Learning (Layer 5)
    learning=LearningMachine(
        knowledge=data_agent_knowledge,
        user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
        user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),

    # Tools
    tools=[
        SQLTools(db_url=db_url),
        ReasoningTools(add_instructions=True),
        analyze_results,
        save_validated_query,
        introspect_schema,
    ],

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

**Key behaviors:**
1. **Search first**: Always searches KB before generating SQL
2. **Learn from corrections**: LearningMachine captures patterns
3. **Provide insights**: Not just data, but analysis
4. **Self-improve**: Offers to save successful queries

### 2. The Knowledge Base

Uses Agno's Knowledge with PgVector for hybrid search:

```python
from agno.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

data_agent_knowledge = Knowledge(
    name="Data Agent Knowledge",
    vector_db=PgVector(
        db_url=db_url,
        table_name="data_agent_knowledge",
        search_type=SearchType.hybrid,  # Semantic + keyword
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    contents_db=agent_db,
    max_results=10,
)
```

**What gets stored:**
- Table metadata with data quality notes
- Validated SQL query patterns
- Business definitions and rules
- Learned corrections (via LearningMachine)

### 3. The System Prompt

The system prompt is **the secret sauce**. It must include:

```markdown
## WORKFLOW (Follow This Exactly)

1. SEARCH KNOWLEDGE FIRST
   - Look for similar questions
   - Find validated query patterns
   - Check data quality notes

2. IDENTIFY TABLES
   - Use semantic model
   - Note column types carefully

3. CHECK DATA QUALITY NOTES
   - Type mismatches (TEXT vs INTEGER)
   - Date formats
   - NULL handling

4. GENERATE SQL
   - Follow SQL rules
   - Handle types correctly

5. VALIDATE RESULTS
   - Zero rows → investigate
   - Unexpected values → check types

6. ANALYZE & EXPLAIN
   - Key findings
   - Context
   - Follow-up suggestions

7. OFFER TO SAVE
   - Successful queries can be saved
   - Future questions benefit

## SEMANTIC MODEL
[Auto-generated from knowledge/tables/]

## DATA QUALITY NOTES (CRITICAL)
[Auto-generated from knowledge/business/]
```

### 4. The Tools

#### `analyze_results`

Transforms raw data into insights:

```python
def analyze_results(
    results: list[dict],
    question: str,
    sql_query: str,
) -> AnalysisResult:
    """
    Returns:
    - Key findings summary
    - Statistics for numeric columns
    - Formatted results table
    - Suggested follow-up questions
    """
```

#### `save_validated_query`

Enables the learning loop:

```python
def save_validated_query(
    name: str,
    question: str,
    query: str,
    summary: str,
    tables_used: list[str],
    data_quality_notes: str,
) -> str:
    """
    Call ONLY after:
    1. Query executed successfully
    2. User confirmed results are correct
    3. User agreed to save
    """
```

#### `introspect_schema`

Layer 6 - Runtime fallback:

```python
def introspect_schema(
    table_name: str | None = None,
    include_sample_data: bool = False,
) -> str:
    """
    When KB info is missing or stale:
    - List all tables (if no table_name)
    - Show columns, types, constraints
    - Optionally include sample data
    """
```

---

## The Learning Loop

This is what makes the agent improve over time:

```
┌─────────────────────────────────────────────────────────────┐
│                    User asks question                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Search Knowledge Base (Layer 1-3)               │
│                                                              │
│  Found similar query?  ─────Yes────▶  Adapt and execute     │
│         │                                                    │
│         No                                                   │
│         ▼                                                    │
│  Generate new SQL with context from semantic model          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execute query                             │
│                                                              │
│  Results look wrong? ─────▶ Self-correct using Layer 6      │
│         │                                                    │
│         OK                                                   │
│         ▼                                                    │
│  Analyze and present insights                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                "Want to save this query?"                    │
│                                                              │
│  Yes ──────▶  save_validated_query() ──▶ KB updated         │
│                                           │                  │
│                                           ▼                  │
│                              Future questions benefit        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                User provides correction                      │
│                                                              │
│  LearningMachine captures ──▶ Memory updated (Layer 5)      │
│                                   │                          │
│                                   ▼                          │
│                      Similar questions improved              │
└─────────────────────────────────────────────────────────────┘
```

---

## Knowledge File Formats

### Table Metadata (`knowledge/tables/*.yaml`)

```yaml
table_name: race_wins
description: Race win records from 1950-2020

columns:
  - name: date
    type: text
    description: Race date in 'DD Mon YYYY' format
    quality_notes:
      - "TEXT format, not DATE"
      - "Use TO_DATE(date, 'DD Mon YYYY') for date operations"
      - "Extract year: EXTRACT(YEAR FROM TO_DATE(date, 'DD Mon YYYY'))"

  - name: name
    type: text
    description: Full name of winning driver

  - name: name_tag
    type: text
    description: Driver abbreviation (HAM, VER, etc.)
    quality_notes:
      - "Different column name than drivers_championship.driver_tag"

use_cases:
  - Count wins by driver or team
  - Analyze wins by circuit
  - Track win streaks

related_tables:
  - drivers_championship
  - race_results
```

### Business Definitions (`knowledge/business/metrics.yaml`)

```yaml
metrics:
  - name: Race Win
    definition: First place finish in a race
    table: race_wins
    calculation: COUNT(*) GROUP BY driver

  - name: World Championship
    definition: First place in season standings
    table: drivers_championship
    calculation: position = '1' (TEXT comparison!)

business_rules:
  - Constructors Championship started in 1958
  - Points systems changed over years
  - Team names vary slightly across years

common_gotchas:
  - issue: position column type mismatch
    affected_tables: [drivers_championship, constructors_championship]
    solution: |
      drivers_championship.position is TEXT: use '1'
      constructors_championship.position is INTEGER: use 1
```

### Validated Queries (`knowledge/queries/*.sql`)

```sql
-- @name: most_race_wins_by_year
-- @question: Who won the most races in {year}?
-- @tables: race_wins
-- @quality_notes: Uses TO_DATE for date parsing

SELECT
    name AS driver,
    COUNT(*) AS wins
FROM race_wins
WHERE EXTRACT(YEAR FROM TO_DATE(date, 'DD Mon YYYY')) = :year
GROUP BY name
ORDER BY wins DESC
LIMIT 10;
```

---

## Evaluation Framework

### Test Case Structure

```python
@dataclass
class TestCase:
    question: str
    expected_values: list[str]  # Strings that must appear in response
    category: str               # basic, aggregation, data_quality, complex
    difficulty: str             # easy, medium, hard
    tags: list[str]             # For filtering
```

### Running Evals

```bash
# All tests
python -m da.evals.run_evals

# By category
python -m da.evals.run_evals --category data_quality

# By difficulty
python -m da.evals.run_evals --difficulty hard

# Show stats
python -m da.evals.run_evals --stats
```

### Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| `basic` | Simple queries | Core functionality |
| `aggregation` | GROUP BY, COUNT | SQL generation |
| `data_quality` | Type handling | Data quality notes |
| `complex` | Multi-table | Advanced SQL |
| `edge_case` | NULLs, errors | Error handling |

---

## Workflows

### Data Validation Workflow

```python
from agno.workflow import Workflow

data_validation = Workflow(
    name="Data Validation",
    steps=[
        # Step 1: Get table list
        # Step 2: Check row counts
        # Step 3: Check null rates
        # Step 4: Check type consistency
        # Step 5: Report anomalies
    ]
)
```

### Metrics Report Workflow

```python
report_workflow = Workflow(
    name="Metrics Report",
    steps=[
        # Step 1: Gather key metrics
        # Step 2: Compare to historical
        # Step 3: Generate insights
        # Step 4: Format report
    ]
)
```

---

## Bring Your Own Data

### Step 1: Create Dataset Directory

```
datasets/my_data/
├── schema.yaml          # Table definitions
├── data/                # CSV/Parquet files
│   ├── users.csv
│   └── orders.csv
├── business.yaml        # Business rules
└── queries/             # Validated SQL patterns
    └── common.sql
```

### Step 2: Define Schema

```yaml
# schema.yaml
tables:
  - name: users
    description: User accounts
    columns:
      - name: id
        type: integer
        primary_key: true
      - name: email
        type: text
        quality_notes:
          - "Always lowercase"
      - name: created_at
        type: timestamp
```

### Step 3: Load Dataset

```bash
python -m da.scripts.load_dataset my_data
```

### Step 4: Load Knowledge

```bash
python -m da.scripts.load_knowledge my_data
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_USER` | No | `ai` | Database user |
| `DB_PASS` | No | `ai` | Database password |
| `DB_DATABASE` | No | `ai` | Database name |
| `DATA_AGENT_MODEL` | No | `gpt-4.1` | Model to use |
| `DATA_AGENT_DEBUG` | No | `false` | Enable debug logging |
| `EXA_API_KEY` | No | - | Exa API for research |

### Configuration File (`da/config.py`)

```python
from pydantic_settings import BaseSettings

class DataAgentConfig(BaseSettings):
    model: str = "gpt-4.1"
    max_results: int = 10
    default_limit: int = 50
    debug: bool = False

    class Config:
        env_prefix = "DATA_AGENT_"
```

---

## Success Criteria

The data agent is successful when:

1. **Accuracy**: >90% pass rate on evaluation suite
2. **Learning**: Demonstrates improvement on repeated similar questions
3. **Analysis**: Provides insights beyond raw query results
4. **Reliability**: Handles data quality edge cases gracefully
5. **Usability**: One-command setup, clear documentation
6. **Extensibility**: Easy to add new datasets and knowledge

---

## Implementation Phases

### Phase 1: Core Agent ✅
- [x] Agent with LearningMachine
- [x] Knowledge base setup
- [x] Basic tools (SQL, analyze, introspect)
- [x] Semantic model builder
- [x] Test cases and evaluation runner

### Phase 2: Polish (Current)
- [ ] YAML-based knowledge files
- [ ] Configuration management
- [ ] Better error handling
- [ ] Structured outputs
- [ ] Enhanced analysis tool

### Phase 3: Workflows
- [ ] Data validation workflow
- [ ] Metrics report workflow
- [ ] Custom workflow builder

### Phase 4: Production
- [ ] Performance optimization
- [ ] Caching layer
- [ ] Rate limiting
- [ ] Monitoring and alerting

---

## References

- [OpenAI Data Agent Article](https://openai.com/index/how-openai-built-its-data-agent/)
- [Agno Documentation](https://docs.agno.com)
- [Agno Knowledge](https://docs.agno.com/knowledge)
- [Agno Memory](https://docs.agno.com/agents/memory)
- [Agno Workflows](https://docs.agno.com/workflows)
