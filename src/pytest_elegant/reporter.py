"""Custom TerminalReporter for elegant output.

This module provides the ElegantTerminalReporter class that extends pytest's
TerminalReporter to produce clean, minimal, elegant output.
"""

from typing import Any, Optional

from _pytest._code.code import ExceptionChainRepr, ReprEntry, ReprExceptionInfo
from _pytest.config import Config
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter
from rich.console import Console
from rich.syntax import Syntax

from pytest_elegant.utils import (
    BADGE_ERROR,
    BADGE_FAIL,
    BADGE_PASS,
    ansi_bold,
    ansi_bold_yellow,
    ansi_green,
    ansi_red,
    ansi_yellow,
    extract_test_parts,
    format_test_name,
    get_symbols,
    get_terminal_width,
    truncate_test_name,
)


class ElegantTerminalReporter(TerminalReporter):  # type: ignore[misc]
    """Custom reporter that formats pytest output with elegant styling.

    This reporter provides:
    - Minimal, clean output with ✓/✗ symbols
    - Test grouping by file with PASS/FAIL headers
    - Immediate failure display with context
    - Duration information for each test
    - Colored output (green/red/yellow)

    The reporter extends pytest's built-in TerminalReporter to completely
    customize the output format. It suppresses pytest's verbose headers,
    groups tests by file, and displays results in a clean, minimal format
    with elegant aesthetics.

    Configuration options (set in pytest.ini or pyproject.toml):
        - elegant_show_context: Show code context in failure output (default: True)
        - elegant_group_by_file: Group tests by file with headers (default: True)
        - elegant_show_duration: Show test duration (default: True)

    Examples:
        The reporter is automatically registered via the pytest plugin system.
        To disable it, use the --no-elegant flag:

        >>> pytest --no-elegant  # doctest: +SKIP

        Example output:
          PASS  tests/test_math.py
          ✓ test_addition 0.01s
          ✓ test_subtraction 0.01s

          Tests: 2 passed, 2 total
          Duration: 0.02s
    """

    def __init__(self, config: Config, file: Any = None) -> None:
        """Initialize the elegant reporter.

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
        self._show_context = config.getini("elegant_show_context")
        self._group_by_file = config.getini("elegant_group_by_file")
        self._show_duration = config.getini("elegant_show_duration")

        # Get verbosity level for verbose mode support
        # 0 = normal, 1 = -v, 2+ = -vv or more
        self._verbosity = config.option.verbose

        # Get appropriate symbols based on terminal capabilities
        self._symbols = get_symbols()
        self._terminal_width = get_terminal_width()

        # Flag to suppress output during session start header
        self._suppress_output = False

        # Track collection errors separately (they occur during suppressed phase)
        self._collection_errors: list[Any] = []

        # Wrap the terminal writer to intercept writes
        self._original_tw = self._tw
        self._wrap_terminal_writer()

    def _wrap_terminal_writer(self) -> None:
        """Wrap the terminal writer to intercept all writes."""
        original_write = self._tw.write
        original_line = self._tw.line

        def wrapped_write(s: str, **kwargs: Any) -> None:
            if not self._suppress_output:
                original_write(s, **kwargs)

        def wrapped_line(s: str = "", **kwargs: Any) -> None:
            if not self._suppress_output:
                original_line(s, **kwargs)

        self._tw.write = wrapped_write  # type: ignore[method-assign,assignment]
        self._tw.line = wrapped_line  # type: ignore[method-assign]

    def pytest_sessionstart(self, session: Any) -> None:
        """Suppress the pytest session start header.

        This prevents pytest from displaying the verbose header information
        (platform, Python version, plugins, rootdir, etc.) for a cleaner
        output with minimal aesthetic.

        Args:
            session: pytest session object
        """
        # Suppress output during session start to hide header
        # Keep it suppressed through collection phase
        self._suppress_output = True
        super().pytest_sessionstart(session)

    def write_line(self, line: str | bytes = "", **markup: bool) -> None:
        """Override to suppress output when needed.

        Args:
            line: text to write
            **markup: color/style markup options
        """
        # Suppress output during session start header and collection
        if self._suppress_output:
            return
        super().write_line(line, **markup)

    def write(self, content: str, *, flush: bool = False, **markup: bool) -> None:
        """Override to suppress output when needed.

        Args:
            content: text to write
            flush: whether to flush output
            **markup: color/style markup options
        """
        # Suppress output during session start header and collection
        if self._suppress_output:
            return
        super().write(content, flush=flush, **markup)

    def write_sep(
        self,
        sep: str,
        title: Optional[str] = None,
        fullwidth: Optional[int] = None,
        **markup: bool,
    ) -> None:
        """Override to suppress separator lines.

        Elegant output doesn't use separator lines like pytest's
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

    def pytest_runtest_logstart(
        self, nodeid: str, location: tuple[str, int | None, str]
    ) -> None:
        """Override to suppress test start logging.

        Args:
            nodeid: test node ID
            location: test location (file, line, name)
        """
        # Suppress the test start log - we handle formatting ourselves
        pass

    def _write_progress_information_filling_space(self) -> None:
        """Override to suppress the progress indicator [X%].

        This prevents pytest from writing the "[100%]" progress indicator.
        """
        # Suppress progress percentage - we handle formatting ourselves
        pass

    def pytest_collection_finish(self, session: Any) -> None:
        """Suppress the 'collected X items' message.

        Args:
            session: pytest session object
        """
        # Don't print "collected X items" - we want minimal output
        # Re-enable output after collection (was suppressed since sessionstart)
        self._suppress_output = False

    def pytest_collectreport(self, report: Any) -> None:
        """Track collection errors.

        Collection happens while output is suppressed, so we capture errors
        here to display them later in the summary.

        Args:
            report: collection report object
        """
        super().pytest_collectreport(report)
        if report.failed:
            self._total_errors += 1
            self._collection_errors.append(report)

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Process and format test results as they come in.

        This is the main hook method that formats each test result elegantly.
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
        # Only process the "call" phase (actual test execution) and setup phase skips
        if report.when != "call":
            # Handle setup/teardown failures (e.g., missing fixture, fixture error)
            if report.failed and report.when in ("setup", "teardown"):
                self._total_errors += 1
                self._collection_errors.append(report)
                # Call parent with suppressed output to update internal tracking
                old_suppress = self._suppress_output
                self._suppress_output = True
                super().pytest_runtest_logreport(report)
                self._suppress_output = old_suppress
                return
            # Handle skips that happen during setup (e.g., @pytest.mark.skip)
            if report.skipped and report.when == "setup":
                pass  # Continue processing skipped tests
            else:
                return

        # Extract file path from nodeid (format: "tests/test_foo.py::test_bar")
        nodeid = report.nodeid
        if "::" in nodeid:
            file_path = nodeid.split("::", 1)[0]
        else:
            file_path = nodeid

        # Get test symbol
        symbol = self._get_symbol(report)

        # Track statistics
        if report.passed:
            self._total_passed += 1
        elif report.failed:
            self._total_failed += 1
        elif report.skipped:
            # Check if this is xfailed (expected to fail and did fail)
            if hasattr(report, "wasxfail"):
                self._total_xfailed += 1
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

        # Call parent to handle internal tracking, but suppress its output
        old_suppress = self._suppress_output
        self._suppress_output = True
        super().pytest_runtest_logreport(report)
        self._suppress_output = old_suppress

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
            from pytest_elegant.utils import truncate_path
            display_path = truncate_path(file_path, 60)

        # Print file header with PASS/FAIL status
        has_failures = self._file_has_failures.get(file_path, False)
        if has_failures:
            self.write_line(f"\n  {BADGE_FAIL}  {display_path}", bold=True)
        else:
            self.write_line(f"\n  {BADGE_PASS}  {display_path}", bold=True)

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

        # Format test name in Pest style (remove test_ prefix, replace _ with spaces)
        formatted_test_name = format_test_name(test_name)

        # Build display name
        display_name = formatted_test_name

        # Add class name if present (for test classes)
        if class_name:
            display_name = f"{class_name}::{formatted_test_name}"

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

        # Color only the symbol (Pest style), not the test name
        colored_symbol = symbol
        if hasattr(report, "wasxfail") and report.passed:
            colored_symbol = ansi_yellow(symbol)
        elif hasattr(report, "wasxfail") and report.skipped:
            colored_symbol = ansi_yellow(symbol)
        elif report.passed:
            colored_symbol = ansi_green(symbol)
        elif report.failed:
            colored_symbol = ansi_red(symbol)
        elif report.skipped:
            colored_symbol = ansi_yellow(symbol)

        # Build the result line with right-aligned duration (Pest style)
        # The symbol is colored, but test name and duration are not
        left_part = f"  {colored_symbol} {display_name}"

        if self._show_duration:
            duration_str = self._format_duration(report.duration)
            # Calculate padding to right-align duration
            # Reserve 1 character for right margin
            # Need to account for ANSI codes in length calculation
            visible_len = 2 + 1 + 1 + len(display_name)  # "  " + symbol + " " + name
            duration_len = len(duration_str)
            padding_needed = max(1, self._terminal_width - visible_len - duration_len - 1)
            result_line = f"{left_part}{' ' * padding_needed}{duration_str}"
        else:
            result_line = left_part

        # Write the line without additional coloring
        self.write_line(result_line)

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

    def _print_code_context(self, file_path: str, failing_line: int, context_before: int = 3, context_after: int = 3) -> None:
        """Print code context around a failing line with syntax highlighting.

        Reads the source file and displays a few lines of context around the
        failing line, with line numbers, syntax highlighting, and highlighting
        of the specific failing line.

        Args:
            file_path: path to the source file
            failing_line: line number that failed (1-indexed)
            context_before: number of context lines to show before the failure
            context_after: number of context lines to show after the failure
        """
        try:
            # Read the source file
            with open(file_path, 'r', encoding='utf-8') as f:
                source_lines = f.readlines()

            # Calculate range of lines to display (1-indexed)
            start_line = max(1, failing_line - context_before)
            end_line = min(len(source_lines), failing_line + context_after)

            # Get the code snippet
            code_snippet = ''.join(source_lines[start_line - 1:end_line])

            # Create syntax highlighted version using Rich
            syntax = Syntax(
                code_snippet,
                "python",
                theme="ansi_dark",
                line_numbers=True,
                start_line=start_line,
                highlight_lines={failing_line},
                indent_guides=False,
                code_width=None,
            )

            # Create a Rich console that writes to the same output stream
            console = Console(
                file=self._tw._file,
                force_terminal=True,
                width=self._terminal_width,
                legacy_windows=False,
            )

            # Print the syntax-highlighted code
            console.print("  ", syntax, sep="")

        except (FileNotFoundError, IOError, IndexError):
            # If we can't read the file, just skip the context
            pass

    def _format_error_line(self, content: str) -> str:
        """Format an error line with colored exception type if present.

        Applies bold yellow to the exception type and red to the message,
        or plain red when there is no exception type (bare assertion).
        Strips leading whitespace before pattern detection.
        """
        stripped = content.strip()
        if ": " in stripped:
            before_colon, after_colon = stripped.split(": ", 1)
            if " " not in before_colon and before_colon:
                return f"{ansi_bold_yellow(before_colon.split('.')[-1])}{ansi_red(f': {after_colon}')}"
        return ansi_red(stripped)

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

        longrepr = report.longrepr

        if not isinstance(longrepr, (ExceptionChainRepr, ReprExceptionInfo)):
            # Fallback for non-structured cases (should not happen in practice)
            self.write_line(f"  {longrepr}")
            return

        # In very verbose mode (-vv), iterate over chain instead of str(longrepr)
        if self._verbosity >= 2 and isinstance(longrepr, ExceptionChainRepr):
            for traceback, loc, chain_msg in longrepr.chain:
                if chain_msg:
                    self.write_line(f"\n  {ansi_yellow(chain_msg)}")
                for entry in traceback.reprentries:
                    if isinstance(entry, ReprEntry):
                        if entry.reprfileloc:
                            fl = entry.reprfileloc
                            self.write_line(f"\n  {ansi_bold(fl.path)}:{fl.lineno}  {fl.message}")
                        for line in entry.lines:
                            if line.startswith("E "):
                                self.write_line(f"  {self._format_error_line(line[2:])}")
                            elif line.startswith(">"):
                                self.write_line(f"  {ansi_yellow('❱')}  {line[1:].strip()}")
                            else:
                                self.write_line(f"    {line.rstrip()}")
                if loc:
                    first_msg_line = loc.message.split("\n")[0]
                    self.write_line(f"\n  at {ansi_bold(loc.path)}:{loc.lineno}  {first_msg_line}")
            self.write_line("")
            return

        # Extract location from reprcrash
        file_path = None
        line_number = None
        file_location = None

        if longrepr.reprcrash is not None:
            file_path = longrepr.reprcrash.path
            line_number = longrepr.reprcrash.lineno
            file_location = f"{file_path}:{line_number}"

        # Extract message and introspection lines from reprcrash.message
        error_message = None
        error_type = None
        introspection_lines: list[str] = []

        if longrepr.reprcrash is not None:
            message_lines = longrepr.reprcrash.message.split("\n")
            first_line = message_lines[0]
            introspection_lines = [line for line in message_lines[1:] if line.strip()]

            if ": " in first_line:
                before_colon, after_colon = first_line.split(": ", 1)
                if " " not in before_colon and before_colon:
                    error_type = before_colon.split(".")[-1]
                    error_message = after_colon
                else:
                    error_message = first_line
            else:
                error_message = first_line

        # If we still don't have an error message, create one from error type
        if error_message is None and error_type:
            error_message = f"{error_type} occurred."

        # Display the error with elegant formatting
        if error_message:
            first_line = f"{error_type}: {error_message}" if error_type else error_message
            self.write_line(f"  {self._format_error_line(first_line)}")
            for intro_line in introspection_lines:
                self.write_line(f"  {intro_line}")

        # Show file location if available
        if file_location:
            self.write_line(f"\n  at {file_location}")

        # Extract and display code context from the actual file
        if file_path and line_number:
            self._print_code_context(file_path, line_number)

        self.write_line("")

    def pytest_terminal_summary(  # type: ignore[override]
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

        # Print collection errors
        for report in self._collection_errors:
            self.write_line(f"\n  {BADGE_ERROR}  {report.nodeid or 'collection error'}", bold=True)
            longrepr_str = str(report.longrepr)
            for line in longrepr_str.split("\n"):
                self.write_line(f"  {line}")
            self.write_line("")

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

        if self._total_errors > 0:
            summary_parts.append(f"{self._total_errors} error{'s' if self._total_errors > 1 else ''}")

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
        if self._total_failed > 0 or self._total_errors > 0:
            self.write_line(summary_line, red=True, bold=True)
        else:
            self.write_line(summary_line, green=True, bold=True)

        # Print duration
        duration_str = self._format_duration(self._total_duration)
        self.write_line(f"  Duration: {duration_str}", bold=True)
        self.write_line("")
