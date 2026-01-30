"""
Evaluation Runner
=================

Runs test cases against the Data Agent and reports results.

Features:
- Filter by category, difficulty, or tags
- Verbose mode for debugging
- JSON output for CI integration
- Historical comparison (optional)

Usage:
    python -m da.evals.run_evals
    python -m da.evals.run_evals --category basic
    python -m da.evals.run_evals --difficulty easy
    python -m da.evals.run_evals --verbose
    python -m da.evals.run_evals --json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from da.evals.test_cases import (
    CATEGORIES,
    DIFFICULTIES,
    TestCase,
    get_test_cases,
    get_test_stats,
)


@dataclass
class EvalResult:
    """Result of a single test case evaluation.

    Attributes:
        test_case: The test case that was run
        passed: Whether all expected values were found
        missing_values: Expected values not found in response
        response: The agent's response (truncated in non-verbose mode)
        duration_seconds: Time taken to run the test
        error: Error message if the test failed to run
    """

    test_case: TestCase
    passed: bool
    missing_values: list[str]
    response: str
    duration_seconds: float
    error: str | None = None


@dataclass
class EvalReport:
    """Summary report of all evaluations.

    Attributes:
        timestamp: When the evaluation was run
        total: Total number of tests
        passed: Number of tests that passed
        failed: Number of tests that failed
        pass_rate: Percentage of tests that passed
        duration_seconds: Total time taken
        results: Individual test results
        filters: What filters were applied
    """

    timestamp: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    duration_seconds: float
    results: list[EvalResult]
    filters: dict


def run_single_eval(agent, test_case: TestCase, verbose: bool = False) -> EvalResult:
    """Run a single test case.

    Args:
        agent: The Data Agent instance
        test_case: Test case to run
        verbose: Include full response in result

    Returns:
        EvalResult with pass/fail status and details
    """
    start = time.time()
    error = None
    response = ""

    try:
        result = agent.run(test_case.question)
        response = result.content or ""
    except Exception as e:
        error = str(e)
        response = f"Error: {e}"

    duration = time.time() - start

    # Check for expected values (case-insensitive)
    response_lower = response.lower()
    missing = [v for v in test_case.expected_values if v.lower() not in response_lower]

    passed = len(missing) == 0 and error is None

    # Truncate response unless verbose
    if not verbose and len(response) > 500:
        response = response[:500] + "..."

    return EvalResult(
        test_case=test_case,
        passed=passed,
        missing_values=missing,
        response=response,
        duration_seconds=duration,
        error=error,
    )


def run_evals(
    category: str | None = None,
    difficulty: str | None = None,
    tags: list[str] | None = None,
    verbose: bool = False,
    quiet: bool = False,
) -> EvalReport:
    """Run all matching test cases.

    Args:
        category: Filter by category
        difficulty: Filter by difficulty
        tags: Filter by tags
        verbose: Show detailed output
        quiet: Suppress progress output

    Returns:
        EvalReport with all results
    """
    # Import agent here to avoid startup delay when just checking help
    from da.agent import data_agent

    test_cases = get_test_cases(category=category, difficulty=difficulty, tags=tags)

    if not test_cases:
        if not quiet:
            print("No test cases match the specified filters")
        return EvalReport(
            timestamp=datetime.now().isoformat(),
            total=0,
            passed=0,
            failed=0,
            pass_rate=0.0,
            duration_seconds=0.0,
            results=[],
            filters={"category": category, "difficulty": difficulty, "tags": tags},
        )

    if not quiet:
        print(f"Running {len(test_cases)} test cases...")
        if category:
            print(f"  Category: {category}")
        if difficulty:
            print(f"  Difficulty: {difficulty}")
        if tags:
            print(f"  Tags: {', '.join(tags)}")
        print()

    results: list[EvalResult] = []
    start_time = time.time()

    for i, test_case in enumerate(test_cases, 1):
        if not quiet:
            question_preview = test_case.question[:50]
            if len(test_case.question) > 50:
                question_preview += "..."
            print(f"[{i}/{len(test_cases)}] {question_preview}", end=" ", flush=True)

        result = run_single_eval(data_agent, test_case, verbose)
        results.append(result)

        if not quiet:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} ({result.duration_seconds:.1f}s)")

            if not result.passed:
                if result.error:
                    print(f"  Error: {result.error}")
                if result.missing_values:
                    print(f"  Missing: {result.missing_values}")

            if verbose and not result.passed:
                print(f"  Response: {result.response[:200]}...")

    total_duration = time.time() - start_time
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    pass_rate = (passed / len(results) * 100) if results else 0.0

    return EvalReport(
        timestamp=datetime.now().isoformat(),
        total=len(results),
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        duration_seconds=total_duration,
        results=results,
        filters={"category": category, "difficulty": difficulty, "tags": tags},
    )


def print_report(report: EvalReport) -> None:
    """Print evaluation report summary."""
    print()
    print("=" * 60)
    print(f"Results: {report.passed}/{report.total} passed ({report.pass_rate:.1f}%)")
    print(f"Duration: {report.duration_seconds:.1f}s")

    if report.failed > 0:
        print()
        print("Failed tests:")
        for result in report.results:
            if not result.passed:
                tc = result.test_case
                print(f"  [{tc.category}/{tc.difficulty}] {tc.question[:50]}...")
                if result.error:
                    print(f"    Error: {result.error}")
                if result.missing_values:
                    print(f"    Missing: {result.missing_values}")


def save_report(report: EvalReport, filepath: Path) -> None:
    """Save evaluation report to JSON file."""
    # Convert to serializable format
    data = {
        "timestamp": report.timestamp,
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "pass_rate": report.pass_rate,
        "duration_seconds": report.duration_seconds,
        "filters": report.filters,
        "results": [
            {
                "question": r.test_case.question,
                "category": r.test_case.category,
                "difficulty": r.test_case.difficulty,
                "passed": r.passed,
                "missing_values": r.missing_values,
                "duration_seconds": r.duration_seconds,
                "error": r.error,
            }
            for r in report.results
        ],
    }

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Data Agent evaluations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Categories: {", ".join(CATEGORIES)}
Difficulties: {", ".join(DIFFICULTIES)}

Examples:
  python -m da.evals.run_evals
  python -m da.evals.run_evals --category basic
  python -m da.evals.run_evals --difficulty easy
  python -m da.evals.run_evals --verbose
  python -m da.evals.run_evals --json > results.json
""",
    )

    parser.add_argument(
        "--category",
        "-c",
        choices=CATEGORIES,
        help="Run only tests in this category",
    )
    parser.add_argument(
        "--difficulty",
        "-d",
        choices=DIFFICULTIES,
        help="Run only tests of this difficulty",
    )
    parser.add_argument(
        "--tags",
        "-t",
        nargs="+",
        help="Run only tests with any of these tags",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output including responses",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Save results to file",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show test case statistics and exit",
    )

    args = parser.parse_args()

    # Show stats and exit
    if args.stats:
        stats = get_test_stats()
        print(f"Total test cases: {stats['total']}")
        print()
        print("By category:")
        for cat, count in stats["by_category"].items():
            print(f"  {cat}: {count}")
        print()
        print("By difficulty:")
        for diff, count in stats["by_difficulty"].items():
            print(f"  {diff}: {count}")
        return 0

    # Run evaluations
    report = run_evals(
        category=args.category,
        difficulty=args.difficulty,
        tags=args.tags,
        verbose=args.verbose,
        quiet=args.json,
    )

    # Output results
    if args.json:
        data = {
            "timestamp": report.timestamp,
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "pass_rate": report.pass_rate,
            "duration_seconds": report.duration_seconds,
        }
        print(json.dumps(data, indent=2))
    else:
        print_report(report)

    # Save if requested
    if args.save:
        save_report(report, args.save)
        print(f"\nResults saved to {args.save}")

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
