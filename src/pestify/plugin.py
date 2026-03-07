"""Pytest plugin hooks for Pestify.

This module provides the core pytest hooks that integrate Pestify's
custom reporter into pytest's test execution flow.
"""

import sys
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


@pytest.hookimpl(trylast=True)
def pytest_configure(config: Config) -> None:
    """Configure pytest to use Pestify's custom reporter.

    This hook runs after pytest's own configuration to replace the default
    TerminalReporter with our PestifyTerminalReporter.

    Uses trylast=True to run after pytest's terminal reporter is registered.

    Args:
        config: pytest configuration object
    """
    # Don't replace reporter if pestify is disabled
    if config.option.no_pestify:
        return

    # Don't replace reporter if collecting only
    if config.getoption("--collect-only", False):
        return

    # Replace the terminal reporter with ours
    if config.option.verbose >= 0:
        # Import here to avoid circular dependencies
        from pestify.reporter import PestifyTerminalReporter

        # Get the standard terminal reporter that pytest just registered
        standard_reporter = config.pluginmanager.get_plugin("terminalreporter")

        if standard_reporter and not isinstance(standard_reporter, PestifyTerminalReporter):
            # Unregister pytest's terminal reporter
            config.pluginmanager.unregister(standard_reporter)

            # Create and register our custom reporter
            reporter = PestifyTerminalReporter(config, sys.stdout)
            config.pluginmanager.register(reporter, "terminalreporter")


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

    # Get symbols (with unicode detection)
    from pestify.utils import get_symbols
    symbols = get_symbols()

    # Handle xpassed (expected to fail but passed)
    if hasattr(report, "wasxfail") and report.outcome == "passed":
        return ("xpassed", symbols["xpassed"], ("XPASS", {"yellow": True, "bold": True}))

    # Handle xfailed (expected to fail and did)
    if hasattr(report, "wasxfail") and report.outcome == "skipped":
        return ("xfailed", symbols["xfailed"], ("XFAIL", {"yellow": True}))

    # Standard outcomes
    if report.outcome == "passed":
        return ("passed", symbols["passed"], ("PASSED", {"green": True}))
    elif report.outcome == "failed":
        return ("failed", symbols["failed"], ("FAILED", {"red": True}))
    elif report.outcome == "skipped":
        return ("skipped", symbols["skipped"], ("SKIPPED", {"yellow": True}))

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
