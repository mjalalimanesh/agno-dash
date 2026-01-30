"""
Context Module
==============

The 6 Layers of Context for the Data Agent.

This module provides modular context builders that can be composed
to create the agent's system prompt and knowledge base.

Layers:
    1. Table Metadata (semantic_model.py)
    2. Human Annotations (business_rules.py)
    3. Query Patterns (query_patterns.py)
    4. Institutional Knowledge (MCP - configured in agent.py)
    5. Memory (LearningMachine - configured in agent.py)
    6. Runtime Context (introspect tool - in tools/)
"""

from da.context.business_rules import (
    build_business_context,
    load_business_rules,
)
from da.context.query_patterns import (
    load_query_patterns,
)
from da.context.semantic_model import (
    build_semantic_model,
    format_semantic_model,
    load_table_metadata,
)

__all__ = [
    # Layer 1: Table Metadata
    "load_table_metadata",
    "build_semantic_model",
    "format_semantic_model",
    # Layer 2: Business Rules
    "load_business_rules",
    "build_business_context",
    # Layer 3: Query Patterns
    "load_query_patterns",
]
