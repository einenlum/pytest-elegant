"""Custom TerminalReporter for Pest-style output.

This module provides the PestifyTerminalReporter class that extends pytest's
TerminalReporter to produce clean, minimal output matching Pest PHP's aesthetic.
"""

from typing import Any, Optional

from _pytest.config import Config
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter


class PestifyTerminalReporter(TerminalReporter):
    """Custom reporter that formats pytest output in Pest style.

    This reporter provides:
    - Minimal, clean output with ✓/✗ symbols
    - Test grouping by file with PASS/FAIL headers
    - Immediate failure display with context
    - Duration information for each test
    - Colored output (green/red/yellow)
    """

    def __init__(self, config: Config) -> None:
        """Initialize the Pestify reporter.

        Args:
            config: pytest configuration object
        """
        super().__init__(config)
        self._current_file: Optional[str] = None
        self._file_results: dict[str, list[tuple[TestReport, str]]] = {}
        self._file_has_failures: dict[str, bool] = {}
        self._total_passed = 0
        self._total_failed = 0
        self._total_skipped = 0
        self._total_duration = 0.0

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

    def pytest_collection_finish(self, session: Any) -> None:
        """Suppress the 'collected X items' message.

        Args:
            session: pytest session object
        """
        # Don't print "collected X items" - we want minimal output
        pass

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Process and format test results as they come in.

        This is the main method that formats each test result in Pest style.
        It groups tests by file and displays them with ✓/✗ symbols and durations.

        Args:
            report: test report object containing test results
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

        # Track file changes for grouping
        if file_path != self._current_file:
            # Print previous file's results if there was one
            if self._current_file is not None:
                self._print_file_results(self._current_file)

            self._current_file = file_path
            self._file_results[file_path] = []
            self._file_has_failures[file_path] = False

        # Track test result for this file
        symbol = self._get_symbol(report)
        self._file_results[file_path].append((report, symbol))

        # Track statistics
        if report.passed:
            self._total_passed += 1
        elif report.failed:
            self._total_failed += 1
            self._file_has_failures[file_path] = True
        elif report.skipped:
            self._total_skipped += 1

        self._total_duration += report.duration

        # Call parent to handle internal tracking
        super().pytest_runtest_logreport(report)

    def _get_symbol(self, report: TestReport) -> str:
        """Get the appropriate symbol for a test result.

        Args:
            report: test report object

        Returns:
            Symbol string (✓, ⨯, -, etc.)
        """
        if report.passed:
            return "✓"
        elif report.failed:
            return "⨯"
        elif report.skipped:
            return "-"
        else:
            return "?"

    def _print_file_results(self, file_path: str) -> None:
        """Print all results for a given test file.

        Args:
            file_path: path to the test file
        """
        if file_path not in self._file_results:
            return

        results = self._file_results[file_path]
        if not results:
            return

        # Print file header with PASS/FAIL status
        has_failures = self._file_has_failures.get(file_path, False)
        if has_failures:
            self.write_line(f"\n  FAIL  {file_path}", red=True, bold=True)
        else:
            self.write_line(f"\n  PASS  {file_path}", green=True, bold=True)

        # Print each test result
        for report, symbol in results:
            self._print_test_result(report, symbol)

        # Clear results for this file
        del self._file_results[file_path]

    def _print_test_result(self, report: TestReport, symbol: str) -> None:
        """Print a single test result line.

        Args:
            report: test report object
            symbol: symbol to display (✓, ⨯, etc.)
        """
        # Extract test name from nodeid
        if "::" in report.nodeid:
            _, test_name = report.nodeid.split("::", 1)
        else:
            test_name = report.nodeid

        # Format duration
        duration_str = self._format_duration(report.duration)

        # Build the result line
        result_line = f"  {symbol} {test_name} {duration_str}"

        # Print with appropriate color
        if report.passed:
            self.write_line(result_line, green=True)
        elif report.failed:
            self.write_line(result_line, red=True)
            # Show failure details immediately
            self._print_failure_details(report)
        elif report.skipped:
            self.write_line(result_line, yellow=True)

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

        Args:
            report: test report object with failure information
        """
        if not report.longrepr:
            return

        # Print a separator
        self.write_line("  " + "─" * 40)

        # Parse the longrepr to extract useful information
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

        # Print file location if found
        if file_path and line_number:
            self.write_line(f'    File "{file_path}", line {line_number}')

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

        Args:
            terminalreporter: terminal reporter instance
            exitstatus: pytest exit status code
            config: pytest configuration object
        """
        # Print results for the last file if any
        if self._current_file is not None:
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

        total_tests = self._total_passed + self._total_failed + self._total_skipped
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
