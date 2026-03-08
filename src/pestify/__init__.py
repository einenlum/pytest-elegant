"""Pestify: Pytest plugin for Pest-style output.

Pestify transforms pytest's test output to match Pest PHP's beautiful aesthetic,
providing minimal, clean output with ✓/✗ symbols, file grouping, and colored results.

Features:
    - Clean, minimal output with ✓/✗ symbols instead of dots/F/E
    - Group tests by file with PASS/FAIL headers
    - Show test duration for each test
    - Display failures immediately with code context
    - Colored output (green/red/yellow) for better readability
    - Works with standard pytest `def test_*` syntax
    - No changes to test code required

Installation:
    pip install pestify

Usage:
    Simply install the plugin and run pytest normally. Pestify will automatically
    format the output. To disable, use the --no-pestify flag:

    pytest                # Pest-style output (default)
    pytest --no-pestify   # Standard pytest output

Configuration:
    Options can be set in pytest.ini or pyproject.toml:

    [tool.pytest.ini_options]
    pestify_show_context = true      # Show code context in failures
    pestify_group_by_file = true     # Group tests by file
    pestify_show_duration = true     # Show test durations

Example Output:
    PASS  tests/test_math.py
    ✓ test_addition 0.01s
    ✓ test_subtraction 0.01s

    FAIL  tests/test_user.py
    ✓ test_user_creation 0.05s
    ⨯ test_user_validation 0.03s
    ────────────────────────────────────────
    AssertionError: assert False
      File "tests/test_user.py", line 12
    → 12   assert user.is_valid()

    Tests: 3 passed, 1 failed, 4 total
    Duration: 0.10s

Modules:
    plugin: Pytest hook implementations for integrating Pestify
    reporter: PestifyTerminalReporter class for formatting output
    utils: Helper functions for formatting and terminal operations

Classes:
    PestifyTerminalReporter: Custom terminal reporter for Pest-style output

Functions:
    pytest_configure: Hook to register the custom reporter
    pytest_report_teststatus: Hook to customize test status symbols
"""

__version__ = "0.1.0"

from pestify.reporter import PestifyTerminalReporter
from pestify.plugin import pytest_configure, pytest_report_teststatus

__all__ = [
    "__version__",
    "PestifyTerminalReporter",
    "pytest_configure",
    "pytest_report_teststatus",
]
