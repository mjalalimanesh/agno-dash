"""
Test Cases
==========

Test cases for evaluating the Data Agent.

Each test case includes:
- question: The natural language question
- expected_values: Strings that should appear in the response
- category: For filtering (basic, aggregation, data_quality, complex, edge_case)
- difficulty: easy, medium, hard
- tags: For more granular filtering

The test cases are designed to verify:
1. Basic query functionality
2. Aggregation and grouping
3. Data quality handling (the F1 dataset has intentional type mismatches)
4. Complex multi-table queries
5. Edge cases and error handling
"""

from dataclasses import dataclass, field


@dataclass
class TestCase:
    """A test case for evaluation.

    Attributes:
        question: The natural language question to ask
        expected_values: Strings that must appear in the response
        category: Test category for filtering
        difficulty: easy, medium, or hard
        tags: Additional tags for filtering
        description: Optional explanation of what this tests
    """

    question: str
    expected_values: list[str]
    category: str
    difficulty: str = "medium"
    tags: list[str] = field(default_factory=list)
    description: str = ""


# ============================================================================
# Test Cases by Category
# ============================================================================

BASIC_TESTS = [
    TestCase(
        question="Who won the most races in 2019?",
        expected_values=["Lewis Hamilton", "11"],
        category="basic",
        difficulty="easy",
        tags=["race_wins", "aggregation", "year_filter"],
        description="Basic aggregation with year filter using TO_DATE",
    ),
    TestCase(
        question="Which team won the 2020 constructors championship?",
        expected_values=["Mercedes"],
        category="basic",
        difficulty="easy",
        tags=["constructors_championship", "position_integer"],
        description="Tests position=1 (INTEGER) in constructors_championship",
    ),
    TestCase(
        question="Who won the 2020 drivers championship?",
        expected_values=["Lewis Hamilton"],
        category="basic",
        difficulty="easy",
        tags=["drivers_championship", "position_text"],
        description="Tests position='1' (TEXT) in drivers_championship",
    ),
    TestCase(
        question="How many races were there in 2019?",
        expected_values=["21"],
        category="basic",
        difficulty="easy",
        tags=["race_wins", "count"],
        description="Simple count with year filter",
    ),
]

AGGREGATION_TESTS = [
    TestCase(
        question="Which driver has won the most world championships?",
        expected_values=["Michael Schumacher", "7"],
        category="aggregation",
        difficulty="medium",
        tags=["drivers_championship", "position_text", "all_time"],
        description="All-time aggregation with TEXT position comparison",
    ),
    TestCase(
        question="Which constructor has won the most championships?",
        expected_values=["Ferrari"],
        category="aggregation",
        difficulty="medium",
        tags=["constructors_championship", "position_integer", "all_time"],
        description="All-time aggregation with INTEGER position comparison",
    ),
    TestCase(
        question="Who has the most fastest laps at Monaco?",
        expected_values=["Michael Schumacher"],
        category="aggregation",
        difficulty="medium",
        tags=["fastest_laps", "venue_filter"],
        description="Aggregation with venue filter",
    ),
    TestCase(
        question="How many race wins does Lewis Hamilton have in total?",
        expected_values=["Hamilton"],
        category="aggregation",
        difficulty="easy",
        tags=["race_wins", "driver_filter"],
        description="Simple count for specific driver",
    ),
    TestCase(
        question="Which team has the most race wins all time?",
        expected_values=["Ferrari"],
        category="aggregation",
        difficulty="medium",
        tags=["race_wins", "team_aggregation"],
        description="Team-level aggregation",
    ),
]

DATA_QUALITY_TESTS = [
    TestCase(
        question="Who finished second in the 2019 drivers championship?",
        expected_values=["Valtteri Bottas"],
        category="data_quality",
        difficulty="medium",
        tags=["drivers_championship", "position_text"],
        description="Tests position='2' (TEXT) - common gotcha",
    ),
    TestCase(
        question="Which team came third in the 2020 constructors championship?",
        expected_values=["Racing Point"],
        category="data_quality",
        difficulty="medium",
        tags=["constructors_championship", "position_integer"],
        description="Tests position=3 (INTEGER) - different from drivers_championship",
    ),
    TestCase(
        question="How many races did Ferrari win in 2019?",
        expected_values=["3"],
        category="data_quality",
        difficulty="medium",
        tags=["race_wins", "date_parsing", "team_filter"],
        description="Tests TO_DATE parsing for year extraction",
    ),
    TestCase(
        question="Which drivers finished on the podium at Monaco in 2019?",
        expected_values=["Hamilton", "Vettel", "Bottas"],
        category="data_quality",
        difficulty="hard",
        tags=["race_results", "position_text", "venue_filter"],
        description="Tests position IN ('1','2','3') with venue and year filter",
    ),
]

COMPLEX_TESTS = [
    TestCase(
        question="Compare Ferrari vs Mercedes championship points from 2015-2020",
        expected_values=["Ferrari", "Mercedes"],
        category="complex",
        difficulty="hard",
        tags=["constructors_championship", "comparison", "year_range"],
        description="Multi-year team comparison",
    ),
    TestCase(
        question="Who had the most podium finishes in 2019?",
        expected_values=["Lewis Hamilton"],
        category="complex",
        difficulty="hard",
        tags=["race_results", "position_text", "podium"],
        description="Podium = position IN ('1','2','3')",
    ),
    TestCase(
        question="Which driver won the most races for Ferrari?",
        expected_values=["Michael Schumacher"],
        category="complex",
        difficulty="medium",
        tags=["race_wins", "team_driver"],
        description="Driver wins filtered by team",
    ),
    TestCase(
        question="What was Lewis Hamilton's championship position each year from 2015-2020?",
        expected_values=["Hamilton", "2015", "2016", "2017", "2018", "2019", "2020"],
        category="complex",
        difficulty="hard",
        tags=["drivers_championship", "year_range", "driver_history"],
        description="Driver performance across multiple years",
    ),
]

EDGE_CASE_TESTS = [
    TestCase(
        question="How many retirements were there in 2020?",
        expected_values=["Ret"],
        category="edge_case",
        difficulty="medium",
        tags=["race_results", "special_position"],
        description="Tests position='Ret' handling",
    ),
    TestCase(
        question="List all constructors championships Ferrari has won",
        expected_values=["Ferrari"],
        category="edge_case",
        difficulty="easy",
        tags=["constructors_championship", "list_query"],
        description="List query with specific team",
    ),
    TestCase(
        question="Which drivers were disqualified in races between 2010 and 2020?",
        expected_values=["DSQ"],
        category="edge_case",
        difficulty="hard",
        tags=["race_results", "special_position", "year_range"],
        description="Tests position='DSQ' handling",
    ),
    TestCase(
        question="What's the average points per season for championship winners?",
        expected_values=["points"],
        category="edge_case",
        difficulty="hard",
        tags=["drivers_championship", "statistics"],
        description="Statistical aggregation with filter",
    ),
]

# ============================================================================
# All Test Cases
# ============================================================================

TEST_CASES: list[TestCase] = BASIC_TESTS + AGGREGATION_TESTS + DATA_QUALITY_TESTS + COMPLEX_TESTS + EDGE_CASE_TESTS

# Categories for filtering
CATEGORIES = ["basic", "aggregation", "data_quality", "complex", "edge_case"]
DIFFICULTIES = ["easy", "medium", "hard"]


def get_test_cases(
    category: str | None = None,
    difficulty: str | None = None,
    tags: list[str] | None = None,
) -> list[TestCase]:
    """Get test cases with optional filtering.

    Args:
        category: Filter by category
        difficulty: Filter by difficulty
        tags: Filter by tags (any match)

    Returns:
        List of matching test cases
    """
    result = TEST_CASES

    if category:
        result = [tc for tc in result if tc.category == category]

    if difficulty:
        result = [tc for tc in result if tc.difficulty == difficulty]

    if tags:
        result = [tc for tc in result if any(t in tc.tags for t in tags)]

    return result


def get_test_stats() -> dict:
    """Get statistics about test cases.

    Returns:
        Dictionary with counts by category and difficulty
    """
    stats = {
        "total": len(TEST_CASES),
        "by_category": {},
        "by_difficulty": {},
    }

    for cat in CATEGORIES:
        stats["by_category"][cat] = len([tc for tc in TEST_CASES if tc.category == cat])

    for diff in DIFFICULTIES:
        stats["by_difficulty"][diff] = len([tc for tc in TEST_CASES if tc.difficulty == diff])

    return stats
