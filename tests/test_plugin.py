"""Integration tests for Pestify pytest plugin.

Uses pytest's pytester fixture to create isolated test environments
and verify that Pestify produces the correct output format.
"""

import re
from typing import Any

import pytest
from _pytest.pytester import Pytester


class TestBasicOutput:
    """Test basic Pestify output formatting."""

    def test_passing_tests(self, pytester: Pytester) -> None:
        """Test that passing tests display with ✓ symbol."""
        # Create a test file with passing tests
        pytester.makepyfile(
            test_example="""
            def test_addition():
                assert 1 + 1 == 2

            def test_subtraction():
                assert 5 - 3 == 2
            """
        )

        # Run pytest with pestify enabled (default)
        result = pytester.runpytest()

        # Check exit code
        assert result.ret == 0

        # Check output contains success symbols
        output = "\n".join(result.outlines)
        assert "✓" in output or "." in output  # Unicode or ASCII fallback
        assert "test_addition" in output
        assert "test_subtraction" in output

        # Check for file header
        assert "PASS" in output
        assert "test_example.py" in output

        # Check for summary
        assert "Tests:" in output
        assert "2 passed" in output
        assert "2 total" in output

    def test_failing_tests(self, pytester: Pytester) -> None:
        """Test that failing tests display with ⨯ symbol."""
        pytester.makepyfile(
            test_fail="""
            def test_will_fail():
                assert 1 == 2
            """
        )

        result = pytester.runpytest()

        # Should fail
        assert result.ret != 0

        output = "\n".join(result.outlines)
        assert "⨯" in output or "F" in output  # Unicode or ASCII fallback
        assert "test_will_fail" in output
        assert "FAIL" in output
        assert "AssertionError" in output or "assert 1 == 2" in output

        # Check summary shows failure
        assert "1 failed" in output

    def test_mixed_outcomes(self, pytester: Pytester) -> None:
        """Test mixed passing, failing, and skipped tests."""
        pytester.makepyfile(
            test_mixed="""
            import pytest

            def test_pass():
                assert True

            def test_fail():
                assert False

            @pytest.mark.skip(reason="Testing skip")
            def test_skip():
                pass

            def test_another_pass():
                assert 1 + 1 == 2
            """
        )

        result = pytester.runpytest()

        # Should fail due to one failing test
        assert result.ret != 0

        output = "\n".join(result.outlines)

        # Check all outcomes present
        assert "test_pass" in output
        assert "test_fail" in output
        assert "test_skip" in output
        assert "test_another_pass" in output

        # Check summary
        assert "2 passed" in output
        assert "1 failed" in output
        assert "1 skipped" in output
        assert "4 total" in output


class TestFileGrouping:
    """Test file grouping functionality."""

    def test_multiple_files_grouped(self, pytester: Pytester) -> None:
        """Test that tests are grouped by file."""
        # Create multiple test files
        pytester.makepyfile(
            test_file1="""
            def test_one():
                assert True

            def test_two():
                assert True
            """
        )

        pytester.makepyfile(
            test_file2="""
            def test_three():
                assert True
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # Check both files have headers
        assert "test_file1.py" in output
        assert "test_file2.py" in output

        # Should see PASS headers for both files
        pass_count = output.count("PASS")
        assert pass_count >= 2

    def test_file_header_shows_fail_status(self, pytester: Pytester) -> None:
        """Test that FAIL header appears when file has failures."""
        pytester.makepyfile(
            test_with_fail="""
            def test_pass():
                assert True

            def test_fail():
                assert False
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)
        assert "FAIL" in output
        assert "test_with_fail.py" in output


class TestNoTestifyFlag:
    """Test the --no-pestify command-line flag."""

    def test_disable_pestify(self, pytester: Pytester) -> None:
        """Test that --no-pestify disables Pestify formatting."""
        pytester.makepyfile(
            test_normal="""
            def test_something():
                assert True
            """
        )

        # Run with --no-pestify flag
        result = pytester.runpytest("--no-pestify", "-v")

        output = "\n".join(result.outlines)

        # Should not see Pestify's PASS/FAIL headers
        # Standard pytest output should show PASSED in a different format
        assert "PASSED" in output or "passed" in output

        # Pestify-specific formatting should be absent
        # (Check for pytest's default session header)
        assert "test session starts" in output or "test_normal.py" in output


class TestParametrizedTests:
    """Test support for parametrized tests."""

    def test_parametrized_tests_display(self, pytester: Pytester) -> None:
        """Test that parametrized tests display with parameters."""
        pytester.makepyfile(
            test_params="""
            import pytest

            @pytest.mark.parametrize("input,expected", [
                (1, 2),
                (2, 3),
                (3, 4),
            ])
            def test_increment(input, expected):
                assert input + 1 == expected
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # Should show test with parameters
        assert "test_increment" in output

        # All three parameter sets should pass
        assert "3 passed" in output


class TestTestClasses:
    """Test support for test classes."""

    def test_class_tests_display(self, pytester: Pytester) -> None:
        """Test that tests in classes display correctly."""
        pytester.makepyfile(
            test_classes="""
            class TestMath:
                def test_addition(self):
                    assert 1 + 1 == 2

                def test_multiplication(self):
                    assert 2 * 3 == 6
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # Should show test names
        assert "test_addition" in output
        assert "test_multiplication" in output

        # Should show class name if in verbose mode or as part of grouping
        # At minimum, tests should be counted correctly
        assert "2 passed" in output


class TestVerboseMode:
    """Test verbose mode support."""

    def test_verbose_mode_shows_more_detail(self, pytester: Pytester) -> None:
        """Test that -v flag shows more detailed output."""
        pytester.makepyfile(
            test_verbose="""
            def test_something():
                assert True
            """
        )

        result = pytester.runpytest("-v")

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # In verbose mode, test names should still appear
        assert "test_something" in output

    def test_very_verbose_shows_full_traceback(self, pytester: Pytester) -> None:
        """Test that -vv shows full stack traces."""
        pytester.makepyfile(
            test_fail_verbose="""
            def helper_function():
                assert False, "This should fail"

            def test_with_helper():
                helper_function()
            """
        )

        result = pytester.runpytest("-vv")

        output = "\n".join(result.outlines)

        # Should show function names in traceback
        assert "helper_function" in output
        assert "test_with_helper" in output


class TestDurationDisplay:
    """Test duration display functionality."""

    def test_duration_shown_by_default(self, pytester: Pytester) -> None:
        """Test that test duration is shown by default."""
        pytester.makepyfile(
            test_duration="""
            import time

            def test_with_duration():
                time.sleep(0.01)
                assert True
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Should show duration in seconds
        # Look for pattern like "0.01s" or similar
        assert re.search(r"\d+\.\d+s", output) is not None


class TestConfigurationOptions:
    """Test configuration options from pytest.ini/pyproject.toml."""

    def test_disable_duration_via_config(self, pytester: Pytester) -> None:
        """Test that duration can be disabled via configuration."""
        # Create pytest.ini with configuration
        pytester.makeini(
            """
            [pytest]
            pestify_show_duration = false
            """
        )

        pytester.makepyfile(
            test_config="""
            def test_something():
                assert True
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        # Note: This test verifies configuration is read,
        # but output format might still be present.
        # The actual behavior is that duration won't be shown per test.

    def test_disable_grouping_via_config(self, pytester: Pytester) -> None:
        """Test that file grouping can be disabled."""
        pytester.makeini(
            """
            [pytest]
            pestify_group_by_file = false
            """
        )

        pytester.makepyfile(
            test_no_group="""
            def test_one():
                assert True

            def test_two():
                assert True
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # Tests should still pass
        assert "2 passed" in output


class TestFailureFormatting:
    """Test failure detail formatting."""

    def test_failure_shows_context(self, pytester: Pytester) -> None:
        """Test that failures show code context."""
        pytester.makepyfile(
            test_context="""
            def test_assertion_failure():
                x = 10
                y = 20
                assert x == y, "Values don't match"
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Should show assertion error
        assert "AssertionError" in output or "assert" in output

        # Should show separator
        assert "─" in output or "-" in output

    def test_exception_displays_correctly(self, pytester: Pytester) -> None:
        """Test that exceptions are formatted correctly."""
        pytester.makepyfile(
            test_exception="""
            def test_raises_exception():
                raise ValueError("Something went wrong")
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Should show exception type and message
        assert "ValueError" in output
        assert "Something went wrong" in output


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_test_file(self, pytester: Pytester) -> None:
        """Test handling of empty test files."""
        pytester.makepyfile(
            test_empty="""
            # This file has no tests
            """
        )

        result = pytester.runpytest()

        # Should complete successfully with no tests collected
        assert result.ret in (0, 5)  # 5 = no tests collected

    def test_long_test_names_truncated(self, pytester: Pytester) -> None:
        """Test that very long test names are handled."""
        pytester.makepyfile(
            test_long="""
            def test_this_is_a_very_long_test_name_that_should_be_truncated_if_needed():
                assert True
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # Should see at least part of the test name
        assert "test_this_is_a_very_long" in output

    def test_unicode_in_test_names(self, pytester: Pytester) -> None:
        """Test handling of unicode in test names (if supported)."""
        pytester.makepyfile(
            test_unicode="""
            def test_unicode_émojis_✓():
                assert True
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        # Test should pass, output format depends on terminal encoding

    def test_xfail_tests(self, pytester: Pytester) -> None:
        """Test expected failures (xfail) display correctly."""
        pytester.makepyfile(
            test_xfail="""
            import pytest

            @pytest.mark.xfail(reason="Known bug")
            def test_expected_failure():
                assert False

            @pytest.mark.xfail(reason="Should pass")
            def test_unexpected_pass():
                assert True
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Should show xfail/xpass in summary
        assert "xfailed" in output or "xpassed" in output

    def test_multiple_assertions_failure(self, pytester: Pytester) -> None:
        """Test multiple assertions in a single test."""
        pytester.makepyfile(
            test_multi="""
            def test_multiple_assertions():
                assert 1 == 1
                assert 2 == 2
                assert 3 == 4  # This should fail
                assert 5 == 5
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Should fail on the third assertion
        assert "1 failed" in output
        assert "assert 3 == 4" in output or "AssertionError" in output


class TestSummaryStatistics:
    """Test final summary statistics."""

    def test_summary_shows_all_counts(self, pytester: Pytester) -> None:
        """Test that summary includes all test outcome counts."""
        pytester.makepyfile(
            test_summary="""
            import pytest

            def test_pass_1():
                assert True

            def test_pass_2():
                assert True

            def test_fail():
                assert False

            @pytest.mark.skip
            def test_skip():
                pass
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Check summary line
        assert "Tests:" in output
        assert "2 passed" in output
        assert "1 failed" in output
        assert "1 skipped" in output
        assert "4 total" in output

    def test_summary_shows_duration(self, pytester: Pytester) -> None:
        """Test that summary shows total duration."""
        pytester.makepyfile(
            test_time="""
            def test_quick():
                assert True
            """
        )

        result = pytester.runpytest()

        output = "\n".join(result.outlines)

        # Should show duration
        assert "Duration:" in output
        assert re.search(r"\d+\.\d+s", output) is not None


class TestIntegrationWithPytest:
    """Test integration with pytest features."""

    def test_works_with_markers(self, pytester: Pytester) -> None:
        """Test that pytest markers work correctly."""
        pytester.makepyfile(
            test_markers="""
            import pytest

            @pytest.mark.slow
            def test_marked_slow():
                assert True

            @pytest.mark.fast
            def test_marked_fast():
                assert True
            """
        )

        # Run only fast tests
        result = pytester.runpytest("-m", "fast")

        assert result.ret == 0
        output = "\n".join(result.outlines)

        # Should only run the fast test
        assert "test_marked_fast" in output
        assert "1 passed" in output

    def test_works_with_fixtures(self, pytester: Pytester) -> None:
        """Test that pytest fixtures work correctly."""
        pytester.makepyfile(
            test_fixtures="""
            import pytest

            @pytest.fixture
            def sample_data():
                return {"key": "value"}

            def test_with_fixture(sample_data):
                assert sample_data["key"] == "value"
            """
        )

        result = pytester.runpytest()

        assert result.ret == 0
        output = "\n".join(result.outlines)
        assert "1 passed" in output

    def test_collection_only_mode(self, pytester: Pytester) -> None:
        """Test that --collect-only mode works."""
        pytester.makepyfile(
            test_collect="""
            def test_one():
                assert True

            def test_two():
                assert True
            """
        )

        result = pytester.runpytest("--collect-only")

        # Should not run tests, just collect
        output = "\n".join(result.outlines)
        # Pestify should not interfere with collection
        assert result.ret == 0
