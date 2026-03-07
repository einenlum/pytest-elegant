"""Pytest plugin hooks for Pestify.

This module provides the core pytest hooks that integrate Pestify's
custom reporter into pytest's test execution flow.
"""

from typing import Any, Optional

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from _pytest.reports import TestReport


def pytest_addoption(parser: Parser) -> None:
    """Add command-line options for Pestify.

    Args:
        parser: pytest's command-line parser
    """
    group = parser.getgroup("pestify")
    group.addoption(
        "--no-pestify",
        action="store_true",
        default=False,
        help="Disable Pestify output formatting and use default pytest output",
    )

    # Add configuration options (can also be set in pytest.ini/pyproject.toml)
    parser.addini(
        "pestify_show_context",
        type="bool",
        default=True,
        help="Show code context in failure output (default: True)",
    )
    parser.addini(
        "pestify_group_by_file",
        type="bool",
        default=True,
        help="Group test results by file with PASS/FAIL headers (default: True)",
    )
    parser.addini(
        "pestify_show_duration",
        type="bool",
        default=True,
        help="Show test duration for each test (default: True)",
    )


def pytest_configure(config: Config) -> None:
    """Configure pytest to use Pestify's custom reporter.

    This hook swaps out pytest's default TerminalReporter with our
    PestifyTerminalReporter unless --no-pestify is specified.

    Args:
        config: pytest configuration object
    """
    if config.option.no_pestify:
        return

    # Only apply Pestify reporter for terminal output (not for other reporters)
    if config.option.verbose >= 0 and not config.getoption("--collect-only"):
        # Import here to avoid circular dependencies
        from pestify.reporter import PestifyTerminalReporter

        # Get the standard terminal reporter plugin
        standard_reporter = config.pluginmanager.get_plugin("terminalreporter")

        if standard_reporter:
            # Unregister the standard reporter
            config.pluginmanager.unregister(standard_reporter)

            # Create and register our custom reporter
            pestify_reporter = PestifyTerminalReporter(config)
            config.pluginmanager.register(pestify_reporter, "terminalreporter")


def pytest_report_header(config: Config) -> list[str]:
    """Suppress pytest's verbose header information.

    Returns an empty list to prevent pytest from displaying the standard
    header (platform, Python version, plugins, etc.) for a cleaner output.

    Args:
        config: pytest configuration object

    Returns:
        Empty list to suppress header output
    """
    if config.option.no_pestify:
        return []

    # Return empty list to suppress header lines
    return []


def pytest_report_teststatus(
    report: TestReport, config: Config
) -> Optional[tuple[str, str, tuple[str, dict[str, bool]]]]:
    """Customize test status symbols and output.

    This hook controls what symbols are displayed for test outcomes.
    Returns ✓ for passed tests and ⨯ for failed tests.

    Args:
        report: test report object containing test results
        config: pytest configuration object

    Returns:
        Tuple of (category, letter, word_markup) or None to use defaults
        - category: outcome category (e.g., "passed", "failed")
        - letter: single character shown in brief output
        - word_markup: tuple of (word, markup_dict) for verbose output
    """
    if config.option.no_pestify:
        return None

    # Only customize the 'call' phase (actual test execution)
    if report.when != "call":
        return None

    if report.outcome == "passed":
        return ("passed", "✓", ("PASSED", {"green": True}))
    elif report.outcome == "failed":
        return ("failed", "⨯", ("FAILED", {"red": True}))
    elif report.outcome == "skipped":
        return ("skipped", "-", ("SKIPPED", {"yellow": True}))

    return None


def pytest_collection_finish(session: Any) -> None:
    """Suppress the 'collected X items' message.

    This hook is called after collection is finished. We override it
    to prevent the default "collected X items" message for cleaner output.

    Args:
        session: pytest session object
    """
    config = session.config
    if config.option.no_pestify:
        return

    # The actual suppression is handled in the reporter
    # This hook is here for completeness and future customization
    pass
