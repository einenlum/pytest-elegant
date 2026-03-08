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

    Registers the --no-pestify flag and configuration options that can be
    set in pytest.ini or pyproject.toml. This hook is called during pytest
    initialization before any tests are collected.

    Args:
        parser: pytest's command-line parser for adding options and INI settings

    Configuration options added:
        --no-pestify: Command-line flag to disable Pestify output
        pestify_show_context: Show code context in failures (default: True)
        pestify_group_by_file: Group tests by file (default: True)
        pestify_show_duration: Show test durations (default: True)

    Examples:
        Disable Pestify from command line:
        >>> pytest --no-pestify  # doctest: +SKIP

        Configure in pyproject.toml:
        [tool.pytest.ini_options]
        pestify_show_context = false
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
    TerminalReporter with our PestifyTerminalReporter. It's the core
    integration point that enables Pest-style output.

    Uses trylast=True to run after pytest's terminal reporter is registered,
    ensuring we can safely unregister it and replace it with ours.

    Args:
        config: pytest configuration object containing options and plugin manager

    Behavior:
        - Skips replacement if --no-pestify flag is set
        - Skips replacement if --collect-only is used
        - Unregisters pytest's default terminal reporter
        - Registers PestifyTerminalReporter as the new terminal reporter

    Note:
        Changed from hookwrapper=True to trylast=True in version 0.1.0 to fix
        compatibility with pytest 9.0+ where pytest_configure is a "historic"
        hook incompatible with hookwrapper.

    Examples:
        This hook is automatically called by pytest. To disable:
        >>> pytest --no-pestify  # doctest: +SKIP
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
    header (platform, Python version, plugins, etc.) for a cleaner output
    matching Pest's minimal aesthetic.

    Args:
        config: pytest configuration object

    Returns:
        Empty list to suppress header output. If --no-pestify is set,
        still returns empty list (pytest will use its default behavior).

    Note:
        This is one of several hooks used to achieve Pest's minimal output:
        - pytest_report_header: Suppress platform/version info
        - write_sep in reporter: Suppress separator lines
        - pytest_collection_finish: Suppress "collected X items"

    Examples:
        Standard pytest header (suppressed by this hook):
            =================== test session starts ===================
            platform linux -- Python 3.14.0, pytest-9.0.2
            ...

        Pestify output (starts directly with test results):
            PASS  tests/test_example.py
            ✓ test_something 0.01s
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
    Returns ✓ for passed tests and ⨯ for failed tests (or ASCII
    alternatives if the terminal doesn't support Unicode).

    Args:
        report: test report object containing test results with attributes:
                - when: test phase ("setup", "call", "teardown")
                - outcome: test result ("passed", "failed", "skipped")
                - wasxfail: present if test was marked with xfail/xpass
        config: pytest configuration object

    Returns:
        Tuple of (category, letter, word_markup) or None to use defaults:
        - category: outcome category (e.g., "passed", "failed", "xpassed")
        - letter: single character shown in brief output (✓, ⨯, -, x, X)
        - word_markup: tuple of (word, markup_dict) for verbose output
                      e.g., ("PASSED", {"green": True})

        Returns None if --no-pestify is set or if not in 'call' phase.

    Symbol mapping (Unicode terminals):
        passed  → ✓ (green)
        failed  → ⨯ (red)
        skipped → - (yellow)
        xfailed → x (yellow, expected to fail)
        xpassed → X (yellow bold, unexpected pass)

    Examples:
        For a passing test:
        >>> # Returns: ("passed", "✓", ("PASSED", {"green": True}))  # doctest: +SKIP

        For a failing test:
        >>> # Returns: ("failed", "⨯", ("FAILED", {"red": True}))  # doctest: +SKIP
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

    This hook is called after test collection is finished. We override it
    to prevent the default "collected X items" message for cleaner output
    matching Pest's minimal aesthetic.

    Args:
        session: pytest session object containing collected items and config

    Note:
        The actual suppression of the "collected X items" message is handled
        in PestifyTerminalReporter.pytest_collection_finish(). This hook is
        defined here for completeness and to maintain consistency with pytest's
        hook system, but the main logic is in the reporter.

        If --no-pestify is set, this hook returns immediately without effect.

    Examples:
        Standard pytest output (suppressed):
            collected 3 items

        Pestify output (goes directly to test results):
            PASS  tests/test_example.py
            ✓ test_something 0.01s
    """
    config = session.config
    if config.option.no_pestify:
        return

    # The actual suppression is handled in the reporter
    # This hook is here for completeness and future customization
    pass
