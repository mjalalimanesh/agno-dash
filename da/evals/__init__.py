"""
Data Agent Evaluation Suite
===========================

Test cases and evaluation runner for validating agent performance.

Usage:
    # Run all tests
    python -m da.evals.run_evals

    # Run by category
    python -m da.evals.run_evals --category basic

    # Show statistics
    python -m da.evals.run_evals --stats
"""

from da.evals.test_cases import (
    CATEGORIES,
    DIFFICULTIES,
    TEST_CASES,
    TestCase,
    get_test_cases,
    get_test_stats,
)

__all__ = [
    "TEST_CASES",
    "TestCase",
    "CATEGORIES",
    "DIFFICULTIES",
    "get_test_cases",
    "get_test_stats",
]
