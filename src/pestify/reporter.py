"""Custom TerminalReporter for Pest-style output.

This module provides the PestifyTerminalReporter class that extends pytest's
TerminalReporter to produce clean, minimal output matching Pest PHP's aesthetic.
"""

from typing import Any, Optional

from _pytest.config import Config
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter

from pestify.utils import (
    extract_test_parts,
    get_symbols,
    get_terminal_width,
    truncate_test_name,
)


class PestifyTerminalReporter(TerminalReporter):
    """Custom reporter that formats pytest output in Pest style.

    This reporter provides:
    - Minimal, clean output with ✓/✗ symbols
    - Test grouping by file with PASS/FAIL headers
    - Immediate failure display with context
    - Duration information for each test
    - Colored output (green/red/yellow)

    The reporter extends pytest's built-in TerminalReporter to completely
    customize the output format. It suppresses pytest's verbose headers,
    groups tests by file, and displays results in a clean, minimal format
    inspired by Pest PHP's test output.

    Configuration options (set in pytest.ini or pyproject.toml):
        - pestify_show_context: Show code context in failure output (default: True)
        - pestify_group_by_file: Group tests by file with headers (default: True)
        - pestify_show_duration: Show test duration (default: True)

    Examples:
        The reporter is automatically registered via the pytest plugin system.
        To disable it, use the --no-pestify flag:

        >>> pytest --no-pestify  # doctest: +SKIP

        Example output:
          PASS  tests/test_math.py
          ✓ test_addition 0.01s
          ✓ test_subtraction 0.01s

          Tests: 2 passed, 2 total
          Duration: 0.02s
    """

    def __init__(self, config: Config, file: Any = None) -> None:
        """Initialize the Pestify reporter.

        Sets up the reporter with configuration options, initializes tracking
        variables for test results and file grouping, and detects terminal
        capabilities for Unicode symbol support.

        Args:
            config: pytest configuration object containing options and settings
            file: optional file object to write to (defaults to sys.stdout)

        Note:
            This is typically called automatically by pytest during plugin
            registration. The reporter reads configuration from pytest.ini
            or pyproject.toml to customize behavior.
        """
        super().__init__(config, file)
        self._current_file: Optional[str] = None
        self._file_results: dict[str, list[tuple[TestReport, str]]] = {}
        self._file_has_failures: dict[str, bool] = {}
        self._total_passed = 0
        self._total_failed = 0
        self._total_skipped = 0
        self._total_xfailed = 0
        self._total_xpassed = 0
        self._total_errors = 0
        self._total_duration = 0.0

        # Read configuration options
        self._show_context = config.getini("pestify_show_context")
        self._group_by_file = config.getini("pestify_group_by_file")
        self._show_duration = config.getini("pestify_show_duration")

        # Get verbosity level for verbose mode support
        # 0 = normal, 1 = -v, 2+ = -vv or more
        self._verbosity = config.option.verbose

        # Get appropriate symbols based on terminal capabilities
        self._symbols = get_symbols()
        self._terminal_width = get_terminal_width()

    def write_sep(
        self,
        sep: str,
        title: Optional[str] = None,
        fullwidth: Optional[int] = None,
        **markup: bool,
    ) -> None:
        """Override to suppress separator lines.

        Pest-style output doesn't use separator lines like pytest's
        "=== test session starts ===" headers.

        Args:
            sep: separator character
            title: optional title text
            fullwidth: optional width override
            **markup: color/style markup options
        """
        # Suppress all separator lines for cleaner output
        pass

    def write_fspath_result(self, nodeid: str, res: Any, **markup: bool) -> None:
        """Override to suppress compact progress output.

        This prevents pytest from writing the compact progress line
        (e.g., "test_file.py ✓✓✓") and lets us handle all output formatting.

        Args:
            nodeid: test node ID
            res: test result
            **markup: color/style markup options
        """
        # Suppress the compact progress output - we handle formatting ourselves
        pass

    def pytest_collection_finish(self, session: Any) -> None:
        """Suppress the 'collected X items' message.

        Args:
            session: pytest session object
        """
        # Don't print "collected X items" - we want minimal output
        pass

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Process and format test results as they come in.

        This is the main hook method that formats each test result in Pest style.
        It groups tests by file and displays them with ✓/✗ symbols and durations.

        The method is called multiple times per test (setup, call, teardown phases)
        but only processes the 'call' phase for regular output. It tracks file
        changes to group tests, accumulates results, and prints file headers when
        all tests in a file are complete.

        Args:
            report: test report object containing test results including:
                    - nodeid: full test path (e.g., "tests/test_foo.py::test_bar")
                    - when: phase of test execution ("setup", "call", or "teardown")
                    - outcome: test result ("passed", "failed", "skipped")
                    - duration: test execution time in seconds
                    - longrepr: detailed failure information if test failed

        Note:
            This method maintains internal state to track file grouping and
            statistics. It updates total counts and duration for the final summary.
        """
        # Only process the "call" phase (actual test execution)
        if report.when != "call":
            # Still need to handle setup/teardown failures
            if report.failed and report.when == "setup":
                super().pytest_runtest_logreport(report)
            return

        # Extract file path from nodeid (format: "tests/test_foo.py::test_bar")
        nodeid = report.nodeid
        if "::" in nodeid:
            file_path, test_name = nodeid.split("::", 1)
        else:
            file_path = nodeid
            test_name = nodeid

        # Get test symbol
        symbol = self._get_symbol(report)

        # Track statistics
        if report.passed:
            self._total_passed += 1
        elif report.failed:
            self._total_failed += 1
        elif report.skipped:
            # Check if this is xfailed or xpassed
            if hasattr(report, "wasxfail"):
                if report.skipped:
                    self._total_xfailed += 1
                else:
                    self._total_skipped += 1
            else:
                self._total_skipped += 1

        # Handle xpassed (expected fail but passed)
        if hasattr(report, "wasxfail") and report.passed:
            self._total_xpassed += 1

        self._total_duration += report.duration

        # Handle grouping by file if enabled
        if self._group_by_file:
            # Track file changes for grouping
            if file_path != self._current_file:
                # Print previous file's results if there was one
                if self._current_file is not None:
                    self._print_file_results(self._current_file)

                self._current_file = file_path
                self._file_results[file_path] = []
                self._file_has_failures[file_path] = False

            # Track test result for this file
            self._file_results[file_path].append((report, symbol))

            # Track failures for file header
            if report.failed:
                self._file_has_failures[file_path] = True
        else:
            # Print results immediately without grouping
            self._print_test_result(report, symbol)

        # Call parent to handle internal tracking
        super().pytest_runtest_logreport(report)

    def _get_symbol(self, report: TestReport) -> str:
        """Get the appropriate symbol for a test result.

        Selects the appropriate Unicode or ASCII symbol based on the test
        outcome and terminal capabilities. Handles special cases like
        xfailed and xpassed tests.

        Args:
            report: test report object with outcome and wasxfail attributes

        Returns:
            Symbol string (✓, ⨯, -, x, X, E, etc.) based on:
            - Test outcome (passed/failed/skipped)
            - Expected failure status (xfail/xpass)
            - Terminal Unicode support

        Examples:
            For a passing test on a Unicode terminal: '✓'
            For a failing test on ASCII terminal: 'F'
            For an expected failure that passed: 'X'
        """
        # Handle xpassed (expected to fail but passed)
        if hasattr(report, "wasxfail") and report.passed:
            return self._symbols["xpassed"]

        # Handle xfailed (expected to fail and did fail)
        if hasattr(report, "wasxfail") and report.skipped:
            return self._symbols["xfailed"]

        # Standard outcomes
        if report.passed:
            return self._symbols["passed"]
        elif report.failed:
            return self._symbols["failed"]
        elif report.skipped:
            return self._symbols["skipped"]
        else:
            return self._symbols.get("error", "?")

    def _print_file_results(self, file_path: str) -> None:
        """Print all results for a given test file.

        Displays a file header (PASS or FAIL) followed by all test results
        for that file. The header color is green for all passing tests or
        red if any test in the file failed.

        Args:
            file_path: path to the test file to print results for

        Note:
            This method is called when all tests in a file have completed,
            or when moving to a new file. It clears the results for the file
            after printing to free memory.
        """
        if file_path not in self._file_results:
            return

        results = self._file_results[file_path]
        if not results:
            return

        # In verbose mode, show full path; otherwise use as-is
        display_path = file_path
        if self._verbosity == 0 and len(file_path) > 60:
            # Only truncate in non-verbose mode
            from pestify.utils import truncate_path
            display_path = truncate_path(file_path, 60)

        # Print file header with PASS/FAIL status
        has_failures = self._file_has_failures.get(file_path, False)
        if has_failures:
            self.write_line(f"\n  FAIL  {display_path}", red=True, bold=True)
        else:
            self.write_line(f"\n  PASS  {display_path}", green=True, bold=True)

        # Print each test result
        for report, symbol in results:
            self._print_test_result(report, symbol)

        # Clear results for this file
        del self._file_results[file_path]

    def _print_test_result(self, report: TestReport, symbol: str) -> None:
        """Print a single test result line.

        Formats and prints a single test result with symbol, name, and duration.
        Handles special cases like parametrized tests and test classes. Includes
        failure details immediately if the test failed and context is enabled.

        Args:
            report: test report object containing test information
            symbol: symbol to display (✓, ⨯, -, etc.) for the test outcome

        Output format:
            "  ✓ test_name 0.12s"  (for passing test)
            "  ⨯ test_name 0.45s"  (for failing test)
            "  - test_skipped"      (for skipped test, if duration disabled)

        Note:
            The output is colored based on the test outcome (green/red/yellow).
            Test names are truncated if too long (except in verbose mode).
        """
        # Extract test parts (file, name, class, parameters)
        file_path, test_name, class_name, parameters = extract_test_parts(report.nodeid)

        # Build display name
        display_name = test_name

        # Add class name if present (for test classes)
        if class_name:
            display_name = f"{class_name}::{test_name}"

        # Add parameters if present (for parametrized tests)
        if parameters:
            display_name = f"{display_name}[{parameters}]"

        # In verbose mode, don't truncate test names
        if self._verbosity == 0:
            # Calculate max length for test name (leave room for symbol, duration, padding)
            # Format: "  ✓ test_name 0.12s"
            # Reserve: 2 (indent) + 2 (symbol + space) + 7 (duration) + 2 (padding) = 13
            max_name_length = max(40, self._terminal_width - 13)

            # Truncate if needed
            if len(display_name) > max_name_length:
                display_name = truncate_test_name(display_name, max_name_length)

        # Build the result line
        result_line = f"  {symbol} {display_name}"

        # Add duration if enabled
        if self._show_duration:
            duration_str = self._format_duration(report.duration)
            result_line += f" {duration_str}"

        # Print with appropriate color based on outcome
        color_kwargs = {}

        # Handle xpassed (expected fail but passed) - yellow/bold
        if hasattr(report, "wasxfail") and report.passed:
            color_kwargs = {"yellow": True, "bold": True}
        # Handle xfailed (expected fail) - yellow
        elif hasattr(report, "wasxfail") and report.skipped:
            color_kwargs = {"yellow": True}
        # Standard outcomes
        elif report.passed:
            color_kwargs = {"green": True}
        elif report.failed:
            color_kwargs = {"red": True}
        elif report.skipped:
            color_kwargs = {"yellow": True}

        self.write_line(result_line, **color_kwargs)

        # Show failure details immediately if failed and context is enabled
        if report.failed and self._show_context:
            self._print_failure_details(report)

    def _format_duration(self, duration: float) -> str:
        """Format test duration for display.

        Args:
            duration: duration in seconds

        Returns:
            Formatted duration string (e.g., "0.12s", "1m 23s")
        """
        if duration < 1:
            return f"{duration:.2f}s"
        elif duration < 60:
            return f"{duration:.1f}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"

    def _print_failure_details(self, report: TestReport) -> None:
        """Print detailed failure information with code context.

        Parses the failure traceback to extract and display the error message,
        file location, line number, and the failing code line with an arrow
        (Pest-style). In very verbose mode (-vv), shows the full stack trace.

        Args:
            report: test report object with failure information in longrepr

        Output includes:
            - Separator line
            - Error message (e.g., "AssertionError: assert False")
            - File location and line number
            - The failing code line with arrow: "→ 4   assert user.is_valid()"

        Note:
            The level of detail shown depends on the verbosity flag:
            - Normal mode: Concise error with key information
            - Verbose mode (-vv): Full stack trace with all details
        """
        if not report.longrepr:
            return

        # Print a separator
        self.write_line("  " + "─" * 40)

        # In very verbose mode (-vv), show full stack trace
        if self._verbosity >= 2:
            # Show the complete traceback
            longrepr_str = str(report.longrepr)
            for line in longrepr_str.split("\n"):
                if line.strip():
                    # Add indentation for consistency
                    self.write_line(f"  {line}")
            self.write_line("")
            return

        # Normal mode: parse the longrepr to extract useful information
        longrepr_str = str(report.longrepr)
        lines = longrepr_str.split("\n")

        # Extract the assertion error or exception message
        error_msg = None
        file_path = None
        line_number = None
        code_line = None

        for i, line in enumerate(lines):
            # Look for the main error message (usually at the start)
            if i == 0 and (
                "AssertionError" in line
                or "Error" in line
                or "Exception" in line
            ):
                error_msg = line.strip()

            # Look for file location and code context
            # Format: "    File \"path/to/file.py\", line 12, in test_name"
            if 'File "' in line and ", line " in line:
                try:
                    # Extract file path and line number
                    parts = line.split('File "')[1].split('", line ')
                    file_path = parts[0]
                    line_number = parts[1].split(",")[0].strip()
                except (IndexError, ValueError):
                    pass

            # Look for the actual code line (usually indented after file location)
            # The code line typically starts with whitespace and might have an arrow
            if file_path and i > 0 and line.strip() and not line.strip().startswith(
                "File"
            ):
                # Check if this looks like code (not an error message)
                stripped = line.strip()
                if (
                    not stripped.startswith("E ")
                    and not stripped.endswith(":")
                    and not "Error" in stripped[:20]
                ):
                    # Remove pytest's ">" marker if present
                    code_line = stripped.lstrip(">").strip()
                    break

        # Print the error message if found
        if error_msg:
            self.write_line(f"  {error_msg}", red=True)
        else:
            # Fallback: print first non-empty line
            for line in lines:
                if line.strip():
                    self.write_line(f"  {line.strip()}", red=True)
                    break

        # Print file location if found (show full path in -v mode)
        if file_path and line_number:
            display_file_path = file_path
            if self._verbosity == 0 and len(file_path) > 60:
                from pestify.utils import truncate_path
                display_file_path = truncate_path(file_path, 60)
            self.write_line(f'    File "{display_file_path}", line {line_number}')

        # Print the code line with an arrow (Pest-style)
        if code_line and line_number:
            self.write_line(f"  → {line_number.rjust(4)}   {code_line}", red=True)
        elif code_line:
            self.write_line(f"  →   {code_line}", red=True)

        self.write_line("")

    def pytest_terminal_summary(
        self,
        terminalreporter: "TerminalReporter",
        exitstatus: int,
        config: Config,
    ) -> None:
        """Print final test summary statistics.

        Displays a summary of all test results with counts and total duration.
        This is called after all tests have completed. It prints any remaining
        file results if grouping is enabled, then shows the final statistics.

        Args:
            terminalreporter: terminal reporter instance (self in this case)
            exitstatus: pytest exit status code (0 = all passed, 1 = failures, etc.)
            config: pytest configuration object

        Output format:
            Tests: 3 passed, 1 failed, 4 total
            Duration: 2.34s

        Note:
            The summary line is colored green if all tests passed, or red if
            any tests failed. Statistics include passed, failed, skipped,
            xfailed, and xpassed tests.
        """
        # Print results for the last file if grouping is enabled
        if self._group_by_file and self._current_file is not None:
            self._print_file_results(self._current_file)
            self._current_file = None

        # Build summary line
        summary_parts = []

        if self._total_passed > 0:
            summary_parts.append(f"{self._total_passed} passed")

        if self._total_failed > 0:
            summary_parts.append(f"{self._total_failed} failed")

        if self._total_skipped > 0:
            summary_parts.append(f"{self._total_skipped} skipped")

        if self._total_xfailed > 0:
            summary_parts.append(f"{self._total_xfailed} xfailed")

        if self._total_xpassed > 0:
            summary_parts.append(f"{self._total_xpassed} xpassed")

        total_tests = (
            self._total_passed
            + self._total_failed
            + self._total_skipped
            + self._total_xfailed
            + self._total_xpassed
        )
        summary_parts.append(f"{total_tests} total")

        # Print summary
        self.write_line("")
        summary_line = "  Tests: " + ", ".join(summary_parts)

        # Color the summary based on results
        if self._total_failed > 0:
            self.write_line(summary_line, red=True, bold=True)
        else:
            self.write_line(summary_line, green=True, bold=True)

        # Print duration
        duration_str = self._format_duration(self._total_duration)
        self.write_line(f"  Duration: {duration_str}", bold=True)
        self.write_line("")
