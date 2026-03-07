"""Sample test file with mixed outcomes for manual testing."""

import pytest


def test_passing_simple():
    """A simple passing test."""
    assert True


def test_passing_calculation():
    """A passing test with calculation."""
    result = sum([1, 2, 3, 4, 5])
    assert result == 15


def test_failing_assertion():
    """A test that fails."""
    result = 10 * 2
    assert result == 25, "Expected 10 * 2 to equal 25"


@pytest.mark.skip(reason="Not implemented yet")
def test_skipped_feature():
    """A test that is skipped."""
    assert False


def test_passing_string_operations():
    """A passing test with strings."""
    text = "Hello, World!"
    assert text.startswith("Hello")
    assert text.endswith("!")
    assert "World" in text


def test_failing_list_operations():
    """A test that fails with list operations."""
    numbers = [1, 2, 3, 4, 5]
    assert len(numbers) == 10
    assert 10 in numbers


@pytest.mark.xfail(reason="Known bug")
def test_xfail_known_issue():
    """A test marked as expected to fail."""
    assert False


@pytest.mark.xfail(reason="Should fail but doesn't")
def test_xpass_unexpected_success():
    """A test marked as xfail but actually passes."""
    assert True


@pytest.mark.parametrize("value,expected", [
    (2, 4),
    (3, 9),
    (4, 16),
])
def test_parametrized_passing(value, expected):
    """Parametrized test that passes."""
    assert value ** 2 == expected


@pytest.mark.parametrize("value,expected", [
    (2, 5),
    (3, 10),
    (4, 20),
])
def test_parametrized_failing(value, expected):
    """Parametrized test that fails."""
    assert value ** 2 == expected


class TestClassExample:
    """Example test class with mixed outcomes."""

    def test_class_passing(self):
        """A passing test in a class."""
        assert 1 + 1 == 2

    def test_class_failing(self):
        """A failing test in a class."""
        assert 2 + 2 == 5

    @pytest.mark.skip(reason="Class test skip")
    def test_class_skipped(self):
        """A skipped test in a class."""
        assert False
