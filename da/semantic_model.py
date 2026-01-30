"""
Semantic Model (Backward Compatibility)
=======================================

This module provides backward compatibility for imports.
The actual implementation is in da/context/semantic_model.py

Usage:
    from da.semantic_model import SEMANTIC_MODEL_STR
"""

# Re-export from the context module
from da.context.semantic_model import (
    SEMANTIC_MODEL,
    SEMANTIC_MODEL_STR,
    build_semantic_model,
    format_semantic_model,
    load_table_metadata,
)

__all__ = [
    "SEMANTIC_MODEL",
    "SEMANTIC_MODEL_STR",
    "build_semantic_model",
    "format_semantic_model",
    "load_table_metadata",
]
