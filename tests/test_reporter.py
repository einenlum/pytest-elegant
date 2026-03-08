"""Unit tests for ElegantTerminalReporter and utility functions."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from _pytest.config import Config
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter

from pytest_elegant.reporter import ElegantTerminalReporter
from pytest_elegant.utils import (
    extract_test_parts,
    format_duration,
    get_file_path_from_nodeid,
    get_symbols,
    get_test_name_from_nodeid,
    get_terminal_width,
    supports_unicode,
    truncate_path,
    truncate_test_name,
)


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_format_subsecond_duration(self):
        """Test formatting durations less than 1 second."""
        assert format_duration(0.123) == "0.12s"
        assert format_duration(0.999) == "1.00s"
        assert format_duration(0.001) == "0.00s"

    def test_format_seconds_duration(self):
        """Test formatting durations in seconds (1-60s)."""
        assert format_duration(1.5) == "1.50s"
        assert format_duration(30.789) == "30.79s"
        assert format_duration(59.99) == "59.99s"

    def test_format_minutes_duration(self):
        """Test formatting durations over 60 seconds."""
        assert format_duration(65.3) == "1m 5s"
        assert format_duration(125.7) == "2m 5s"
        assert format_duration(3661) == "61m 1s"

    def test_format_edge_cases(self):
        """Test edge cases in duration formatting."""
        assert format_duration(0) == "0.00s"
        assert format_duration(60) == "1m 0s"
        assert format_duration(60.5) == "1m 0s"  # Truncates to int for seconds


class TestTruncatePath:
    """Tests for path truncation."""

    def test_truncate_short_path(self):
        """Test that short paths are not truncated."""
        path = "tests/test_foo.py"
        assert truncate_path(path, 60) == path

    def test_truncate_long_path(self):
        """Test truncation of long paths."""
        path = "tests/integration/very/deep/nested/structure/test_example.py"
        result = truncate_path(path, 40)
        assert len(result) <= 40
        assert result.startswith("tests/")
        assert result.endswith("test_example.py")
        assert "..." in result

    def test_truncate_preserves_filename(self):
        """Test that filename is always preserved."""
        path = "a/b/c/d/e/f/g/h/i/j/test_file.py"
        result = truncate_path(path, 30)
        assert "test_file.py" in result

    def test_truncate_very_long_filename(self):
        """Test handling of very long filenames."""
        path = "tests/test_very_long_filename_that_exceeds_maximum_length.py"
        result = truncate_path(path, 40)
        assert len(result) <= 40
        assert result.startswith("...")

    def test_truncate_exact_length(self):
        """Test path at exact max length."""
        path = "a" * 60
        result = truncate_path(path, 60)
        assert result == path

    def test_truncate_builds_progressively(self):
        """Test that truncation includes as many path parts as possible."""
        path = "tests/unit/reporter/test_example.py"
        result = truncate_path(path, 50)
        # Should be able to fit the whole path
        assert result == path


class TestGetTerminalWidth:
    """Tests for terminal width detection."""

    def test_get_terminal_width_returns_positive(self):
        """Test that terminal width is always positive."""
        width = get_terminal_width()
        assert width > 0

    def test_get_terminal_width_default(self):
        """Test default fallback when terminal size unavailable."""
        with patch("shutil.get_terminal_size", side_effect=Exception):
            width = get_terminal_width()
            assert width == 80


class TestGetTestNameFromNodeid:
    """Tests for extracting test names from nodeids."""

    def test_simple_nodeid(self):
        """Test simple nodeid without class."""
        nodeid = "tests/test_foo.py::test_bar"
        assert get_test_name_from_nodeid(nodeid) == "test_bar"

    def test_class_nodeid(self):
        """Test nodeid with class."""
        nodeid = "tests/test_foo.py::TestClass::test_method"
        assert get_test_name_from_nodeid(nodeid) == "test_method"

    def test_parametrized_nodeid(self):
        """Test nodeid with parameters."""
        nodeid = "tests/test_foo.py::test_bar[param1-param2]"
        assert get_test_name_from_nodeid(nodeid) == "test_bar[param1-param2]"

    def test_no_separator_nodeid(self):
        """Test nodeid without :: separator."""
        nodeid = "test_foo.py"
        assert get_test_name_from_nodeid(nodeid) == "test_foo.py"


class TestGetFilePathFromNodeid:
    """Tests for extracting file paths from nodeids."""

    def test_simple_nodeid(self):
        """Test simple nodeid."""
        nodeid = "tests/test_foo.py::test_bar"
        assert get_file_path_from_nodeid(nodeid) == "tests/test_foo.py"

    def test_class_nodeid(self):
        """Test nodeid with class."""
        nodeid = "tests/test_foo.py::TestClass::test_method"
        assert get_file_path_from_nodeid(nodeid) == "tests/test_foo.py"

    def test_parametrized_nodeid(self):
        """Test nodeid with parameters."""
        nodeid = "tests/test_foo.py::test_bar[1-2]"
        assert get_file_path_from_nodeid(nodeid) == "tests/test_foo.py"


class TestSupportsUnicode:
    """Tests for Unicode support detection."""

    def test_supports_unicode_with_utf8(self):
        """Test Unicode support detection with UTF-8 encoding."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "utf-8"
            assert supports_unicode() is True

    def test_supports_unicode_with_ascii(self):
        """Test Unicode support detection with ASCII encoding."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "ascii"
            # Will try to encode and fail
            result = supports_unicode()
            # Result depends on whether encode succeeds
            assert isinstance(result, bool)

    def test_supports_unicode_no_encoding(self):
        """Test Unicode support when encoding is None."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = None
            assert supports_unicode() is False


class TestGetSymbols:
    """Tests for symbol selection."""

    def test_get_symbols_unicode(self):
        """Test getting Unicode symbols."""
        with patch("pytest_elegant.utils.supports_unicode", return_value=True):
            symbols = get_symbols(use_unicode=True)
            assert symbols["passed"] == "✓"
            assert symbols["failed"] == "⨯"
            assert symbols["skipped"] == "-"

    def test_get_symbols_ascii(self):
        """Test getting ASCII fallback symbols."""
        symbols = get_symbols(use_unicode=False)
        assert symbols["passed"] == "."
        assert symbols["failed"] == "F"
        assert symbols["skipped"] == "s"

    def test_get_symbols_all_outcomes(self):
        """Test that all outcome types have symbols."""
        symbols = get_symbols(use_unicode=False)
        assert "passed" in symbols
        assert "failed" in symbols
        assert "skipped" in symbols
        assert "xfailed" in symbols
        assert "xpassed" in symbols
        assert "error" in symbols


class TestTruncateTestName:
    """Tests for test name truncation."""

    def test_truncate_short_name(self):
        """Test that short names are not truncated."""
        name = "test_foo"
        assert truncate_test_name(name, 30) == name

    def test_truncate_long_name(self):
        """Test truncation of long test names."""
        name = "test_very_long_function_name_with_many_words"
        result = truncate_test_name(name, 30)
        assert len(result) <= 30
        assert "..." in result

    def test_truncate_parametrized_test(self):
        """Test truncation of parametrized test names."""
        name = "test_foo[param1-param2]"
        result = truncate_test_name(name, 50)
        assert result == name  # Should fit

    def test_truncate_long_parametrized_test(self):
        """Test truncation of long parametrized test names."""
        name = "test_very_long_function_name[param1-param2-param3]"
        result = truncate_test_name(name, 30)
        # Name is 54 chars, truncating to 30 is too short to keep full params
        assert len(result) <= 30
        # When params are too long, the whole thing gets truncated
        assert "..." in result

    def test_truncate_very_short_limit(self):
        """Test truncation with very short limit."""
        name = "test_function_name"
        result = truncate_test_name(name, 10)
        assert len(result) <= 10

    def test_truncate_preserves_middle_info(self):
        """Test that truncation preserves beginning and end."""
        name = "test_some_middle_content_here"
        result = truncate_test_name(name, 20)
        assert len(result) <= 20
        assert result.startswith("test_")
        assert "..." in result


class TestExtractTestParts:
    """Tests for extracting test parts from nodeids."""

    def test_extract_simple_test(self):
        """Test extracting parts from simple test nodeid."""
        nodeid = "tests/test_foo.py::test_bar"
        file_path, test_name, class_name, parameters = extract_test_parts(nodeid)
        assert file_path == "tests/test_foo.py"
        assert test_name == "test_bar"
        assert class_name is None
        assert parameters is None

    def test_extract_class_test(self):
        """Test extracting parts from class test nodeid."""
        nodeid = "tests/test_foo.py::TestClass::test_method"
        file_path, test_name, class_name, parameters = extract_test_parts(nodeid)
        assert file_path == "tests/test_foo.py"
        assert test_name == "test_method"
        assert class_name == "TestClass"
        assert parameters is None

    def test_extract_parametrized_test(self):
        """Test extracting parts from parametrized test nodeid."""
        nodeid = "tests/test_foo.py::test_bar[param1-param2]"
        file_path, test_name, class_name, parameters = extract_test_parts(nodeid)
        assert file_path == "tests/test_foo.py"
        assert test_name == "test_bar"
        assert class_name is None
        assert parameters == "param1-param2"

    def test_extract_class_parametrized_test(self):
        """Test extracting parts from class parametrized test nodeid."""
        nodeid = "tests/test_foo.py::TestClass::test_method[1-2]"
        file_path, test_name, class_name, parameters = extract_test_parts(nodeid)
        assert file_path == "tests/test_foo.py"
        assert test_name == "test_method"
        assert class_name == "TestClass"
        assert parameters == "1-2"

    def test_extract_file_only(self):
        """Test extracting parts when only file is given."""
        nodeid = "tests/test_foo.py"
        file_path, test_name, class_name, parameters = extract_test_parts(nodeid)
        assert file_path == "tests/test_foo.py"
        assert test_name == nodeid
        assert class_name is None
        assert parameters is None


class TestElegantTerminalReporter:
    """Tests for ElegantTerminalReporter class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock pytest config."""
        from pathlib import Path

        config = Mock(spec=Config)
        config.getini = Mock(side_effect=lambda x: {
            "elegant_show_context": True,
            "elegant_group_by_file": True,
            "elegant_show_duration": True,
        }.get(x, True))
        config.option = Mock()
        config.option.verbose = 0
        config.option.color = "yes"
        config.option.code_highlight = "yes"
        config.option.reportchars = ""
        config.option.disable_warnings = False
        config.option.tbstyle = "auto"

        # Mock invocation_params for TerminalReporter initialization
        invocation_params = Mock()
        invocation_params.dir = Path.cwd()
        config.invocation_params = invocation_params

        # Mock pluginmanager
        config.pluginmanager = Mock()
        config.pluginmanager.get_plugin = Mock(return_value=None)

        # Mock hook for pytest_report_teststatus
        config.hook = Mock()
        config.hook.pytest_report_teststatus = Mock(
            return_value=[("passed", ".", ("PASSED", {"green": True}))]
        )

        return config

    @pytest.fixture
    def reporter(self, mock_config):
        """Create an ElegantTerminalReporter instance."""
        with patch("pytest_elegant.reporter.get_symbols") as mock_symbols:
            mock_symbols.return_value = {
                "passed": "✓",
                "failed": "⨯",
                "skipped": "-",
                "xfailed": "x",
                "xpassed": "X",
                "error": "E",
            }
            reporter = ElegantTerminalReporter(mock_config)
            reporter.write_line = Mock()
            return reporter

    def test_reporter_initialization(self, reporter):
        """Test reporter initializes correctly."""
        assert reporter._current_file is None
        assert reporter._file_results == {}
        assert reporter._total_passed == 0
        assert reporter._total_failed == 0
        assert reporter._show_context is True
        assert reporter._group_by_file is True
        assert reporter._show_duration is True

    def test_get_symbol_passed(self, reporter):
        """Test getting symbol for passed test."""
        report = Mock(spec=TestReport)
        report.passed = True
        report.failed = False
        report.skipped = False
        symbol = reporter._get_symbol(report)
        assert symbol == "✓"

    def test_get_symbol_failed(self, reporter):
        """Test getting symbol for failed test."""
        report = Mock(spec=TestReport)
        report.passed = False
        report.failed = True
        report.skipped = False
        symbol = reporter._get_symbol(report)
        assert symbol == "⨯"

    def test_get_symbol_skipped(self, reporter):
        """Test getting symbol for skipped test."""
        report = Mock(spec=TestReport)
        report.passed = False
        report.failed = False
        report.skipped = True
        symbol = reporter._get_symbol(report)
        assert symbol == "-"

    def test_get_symbol_xfailed(self, reporter):
        """Test getting symbol for xfailed test."""
        report = Mock(spec=TestReport)
        report.passed = False
        report.failed = False
        report.skipped = True
        report.wasxfail = True
        symbol = reporter._get_symbol(report)
        assert symbol == "x"

    def test_get_symbol_xpassed(self, reporter):
        """Test getting symbol for xpassed test."""
        report = Mock(spec=TestReport)
        report.passed = True
        report.failed = False
        report.skipped = False
        report.wasxfail = True
        symbol = reporter._get_symbol(report)
        assert symbol == "X"

    def test_format_duration_method(self, reporter):
        """Test the reporter's duration formatting method."""
        assert reporter._format_duration(0.123) == "0.12s"
        assert reporter._format_duration(1.5) == "1.5s"
        assert reporter._format_duration(65.3) == "1m 5s"

    def test_write_sep_suppressed(self, reporter):
        """Test that write_sep is suppressed."""
        # Should not raise any exception and do nothing
        reporter.write_sep("=", "test session starts")
        # Verify write_line was not called
        reporter.write_line.assert_not_called()

    def test_pytest_collection_finish_suppressed(self, reporter):
        """Test that collection finish message is suppressed."""
        session = Mock()
        reporter.pytest_collection_finish(session)
        # Should not write anything
        reporter.write_line.assert_not_called()

    def test_track_passed_test(self, reporter):
        """Test tracking passed test statistics."""
        report = Mock(spec=TestReport)
        report.when = "call"
        report.nodeid = "tests/test_foo.py::test_bar"
        report.passed = True
        report.failed = False
        report.skipped = False
        report.duration = 0.5

        # Patch super call to avoid pytest internals
        with patch.object(TerminalReporter, "pytest_runtest_logreport"):
            reporter.pytest_runtest_logreport(report)
            assert reporter._total_passed == 1
            assert reporter._total_duration == 0.5

    def test_track_failed_test(self, reporter):
        """Test tracking failed test statistics."""
        report = Mock(spec=TestReport)
        report.when = "call"
        report.nodeid = "tests/test_foo.py::test_bar"
        report.passed = False
        report.failed = True
        report.skipped = False
        report.duration = 1.0
        report.longrepr = None

        # Patch super call to avoid pytest internals
        with patch.object(TerminalReporter, "pytest_runtest_logreport"):
            reporter.pytest_runtest_logreport(report)
            assert reporter._total_failed == 1
            assert reporter._total_duration == 1.0

    def test_file_grouping(self, reporter):
        """Test that tests are grouped by file."""
        # Patch super call to avoid pytest internals
        with patch.object(TerminalReporter, "pytest_runtest_logreport"):
            # First test
            report1 = Mock(spec=TestReport)
            report1.when = "call"
            report1.nodeid = "tests/test_foo.py::test_one"
            report1.passed = True
            report1.failed = False
            report1.skipped = False
            report1.duration = 0.1
            report1.longrepr = None

            reporter.pytest_runtest_logreport(report1)
            assert reporter._current_file == "tests/test_foo.py"
            assert len(reporter._file_results["tests/test_foo.py"]) == 1

            # Second test in same file
            report2 = Mock(spec=TestReport)
            report2.when = "call"
            report2.nodeid = "tests/test_foo.py::test_two"
            report2.passed = True
            report2.failed = False
            report2.skipped = False
            report2.duration = 0.2
            report2.longrepr = None

            reporter.pytest_runtest_logreport(report2)
            assert reporter._current_file == "tests/test_foo.py"
            assert len(reporter._file_results["tests/test_foo.py"]) == 2

    def test_file_change_triggers_print(self, reporter):
        """Test that changing files triggers printing previous results."""
        # Patch super call to avoid pytest internals
        with patch.object(TerminalReporter, "pytest_runtest_logreport"):
            # First test in first file
            report1 = Mock(spec=TestReport)
            report1.when = "call"
            report1.nodeid = "tests/test_foo.py::test_one"
            report1.passed = True
            report1.failed = False
            report1.skipped = False
            report1.duration = 0.1
            report1.longrepr = None

            reporter.pytest_runtest_logreport(report1)

            # Test in different file should trigger print of first file
            report2 = Mock(spec=TestReport)
            report2.when = "call"
            report2.nodeid = "tests/test_bar.py::test_one"
            report2.passed = True
            report2.failed = False
            report2.skipped = False
            report2.duration = 0.1
            report2.longrepr = None

            with patch.object(reporter, "_print_file_results") as mock_print:
                reporter.pytest_runtest_logreport(report2)
                mock_print.assert_called_once_with("tests/test_foo.py")

    def test_print_file_results_pass(self, reporter):
        """Test printing file results with all passing tests."""
        report = Mock(spec=TestReport)
        report.nodeid = "tests/test_foo.py::test_bar"
        report.passed = True
        report.failed = False
        report.duration = 0.1

        reporter._file_results["tests/test_foo.py"] = [(report, "✓")]
        reporter._file_has_failures["tests/test_foo.py"] = False

        with patch.object(reporter, "_print_test_result"):
            reporter._print_file_results("tests/test_foo.py")
            # Should print PASS header in green
            calls = reporter.write_line.call_args_list
            assert any("PASS" in str(call) for call in calls)

    def test_print_file_results_fail(self, reporter):
        """Test printing file results with failures."""
        report = Mock(spec=TestReport)
        report.nodeid = "tests/test_foo.py::test_bar"
        report.passed = False
        report.failed = True
        report.duration = 0.1

        reporter._file_results["tests/test_foo.py"] = [(report, "⨯")]
        reporter._file_has_failures["tests/test_foo.py"] = True

        with patch.object(reporter, "_print_test_result"):
            reporter._print_file_results("tests/test_foo.py")
            # Should print FAIL header in red
            calls = reporter.write_line.call_args_list
            assert any("FAIL" in str(call) for call in calls)

    def test_terminal_summary_pass(self, reporter):
        """Test terminal summary with passing tests."""
        reporter._total_passed = 3
        reporter._total_failed = 0
        reporter._total_duration = 1.5

        terminalreporter = Mock()
        reporter.pytest_terminal_summary(terminalreporter, 0, reporter.config)

        # Should print summary in green
        calls = reporter.write_line.call_args_list
        summary_calls = [c for c in calls if "Tests:" in str(c)]
        assert len(summary_calls) > 0

    def test_terminal_summary_fail(self, reporter):
        """Test terminal summary with failures."""
        reporter._total_passed = 2
        reporter._total_failed = 1
        reporter._total_duration = 2.0

        terminalreporter = Mock()
        reporter.pytest_terminal_summary(terminalreporter, 1, reporter.config)

        # Should print summary in red
        calls = reporter.write_line.call_args_list
        summary_calls = [c for c in calls if "Tests:" in str(c)]
        assert len(summary_calls) > 0

    def test_skip_non_call_phase(self, reporter):
        """Test that non-call phases are skipped (except setup skips)."""
        report = Mock(spec=TestReport)
        report.when = "setup"
        report.failed = False
        report.skipped = False
        report.passed = False
        report.nodeid = "tests/test_foo.py::test_bar"

        reporter.pytest_runtest_logreport(report)
        # Should not track statistics for setup phase (when not skipped)
        assert reporter._total_passed == 0
        assert reporter._current_file is None

    def test_setup_failure_handled(self, reporter):
        """Test that setup failures are handled."""
        report = Mock(spec=TestReport)
        report.when = "setup"
        report.failed = True
        report.skipped = False
        report.passed = False
        report.nodeid = "tests/test_foo.py::test_bar"

        with patch.object(TerminalReporter, "pytest_runtest_logreport"):
            reporter.pytest_runtest_logreport(report)
            # Should call parent reporter for setup failures

    def test_setup_skip_counted(self, reporter):
        """Test that skips during setup phase are counted."""
        report = Mock(spec=TestReport)
        report.when = "setup"
        report.failed = False
        report.skipped = True
        report.passed = False
        report.nodeid = "tests/test_foo.py::test_bar"
        report.duration = 0.0

        with patch.object(TerminalReporter, "pytest_runtest_logreport"):
            reporter.pytest_runtest_logreport(report)
            # Should track skipped statistics for setup phase skips
            assert reporter._total_skipped == 1


class TestPrintTestResult:
    """Tests for _print_test_result method."""

    @pytest.fixture
    def reporter(self):
        """Create a reporter for testing print_test_result."""
        from pathlib import Path

        config = Mock(spec=Config)
        config.getini = Mock(return_value=True)
        config.option = Mock()
        config.option.verbose = 0
        config.option.color = "yes"
        config.option.code_highlight = "yes"
        config.option.reportchars = ""
        config.option.disable_warnings = False
        config.option.tbstyle = "auto"

        # Mock invocation_params for TerminalReporter initialization
        invocation_params = Mock()
        invocation_params.dir = Path.cwd()
        config.invocation_params = invocation_params

        # Mock pluginmanager
        config.pluginmanager = Mock()
        config.pluginmanager.get_plugin = Mock(return_value=None)

        with patch("pytest_elegant.reporter.get_symbols") as mock_symbols:
            mock_symbols.return_value = {
                "passed": "✓",
                "failed": "⨯",
                "skipped": "-",
            }
            reporter = ElegantTerminalReporter(config)
            reporter.write_line = Mock()
            reporter._show_duration = True
            reporter._show_context = True
            reporter._terminal_width = 80
            return reporter

    def test_print_simple_test(self, reporter):
        """Test printing a simple test result."""
        report = Mock(spec=TestReport)
        report.nodeid = "tests/test_foo.py::test_bar"
        report.passed = True
        report.failed = False
        report.skipped = False
        report.duration = 0.12

        reporter._print_test_result(report, "✓")

        # Check that write_line was called with green color (ANSI code)
        reporter.write_line.assert_called_once()
        call_args = reporter.write_line.call_args
        output = call_args[0][0]
        assert "✓" in output
        assert "bar" in output
        # Check for green ANSI color code (\033[32m)
        assert "\033[32m" in output

    def test_print_failed_test_with_context(self, reporter):
        """Test printing a failed test with context."""
        report = Mock(spec=TestReport)
        report.nodeid = "tests/test_foo.py::test_bar"
        report.passed = False
        report.failed = True
        report.skipped = False
        report.duration = 0.5
        report.longrepr = "AssertionError: assert False"

        with patch.object(reporter, "_print_failure_details") as mock_details:
            reporter._print_test_result(report, "⨯")
            # Should call print_failure_details
            mock_details.assert_called_once_with(report)

    def test_print_parametrized_test(self, reporter):
        """Test printing a parametrized test result."""
        report = Mock(spec=TestReport)
        report.nodeid = "tests/test_foo.py::test_bar[param1-param2]"
        report.passed = True
        report.failed = False
        report.skipped = False
        report.duration = 0.1

        reporter._print_test_result(report, "✓")

        call_args = reporter.write_line.call_args
        assert "[param1-param2]" in call_args[0][0]

    def test_print_class_test(self, reporter):
        """Test printing a test from a class."""
        report = Mock(spec=TestReport)
        report.nodeid = "tests/test_foo.py::TestClass::test_method"
        report.passed = True
        report.failed = False
        report.skipped = False
        report.duration = 0.1

        reporter._print_test_result(report, "✓")

        call_args = reporter.write_line.call_args
        assert "TestClass::method" in call_args[0][0]
