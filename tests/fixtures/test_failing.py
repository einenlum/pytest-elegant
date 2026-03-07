"""Sample test file with failing tests for manual testing."""


def test_assertion_failure():
    """Test that fails with a simple assertion."""
    result = 2 + 2
    assert result == 5, "Expected 2 + 2 to equal 5"


def test_type_error():
    """Test that fails with a type error."""
    value = "hello"
    assert value.startswith(123)  # Wrong type


def test_value_error():
    """Test that fails with a value error."""
    numbers = [1, 2, 3]
    assert numbers[5] == 10  # Index out of range


def test_comparison_failure():
    """Test that fails with a comparison."""
    expected = {"name": "Alice", "age": 30}
    actual = {"name": "Bob", "age": 25}
    assert actual == expected


def test_division_by_zero():
    """Test that fails with division by zero."""
    result = 10 / 0
    assert result == 0
