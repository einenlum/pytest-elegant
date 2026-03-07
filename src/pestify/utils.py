"""Helper utility functions for Pestify."""

import os
import shutil
from pathlib import Path


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string like "0.12s" or "1m 23s"

    Examples:
        >>> format_duration(0.123)
        '0.12s'
        >>> format_duration(1.5)
        '1.50s'
        >>> format_duration(65.3)
        '1m 5s'
        >>> format_duration(125.7)
        '2m 5s'
    """
    if seconds < 1:
        return f"{seconds:.2f}s"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"


def truncate_path(path: str, max_length: int = 60) -> str:
    """
    Truncate long file paths intelligently while preserving readability.

    Keeps the filename and important directory structure visible.
    Uses "..." to indicate truncation.

    Args:
        path: The file path to truncate
        max_length: Maximum length of the returned path

    Returns:
        Truncated path string

    Examples:
        >>> truncate_path("tests/integration/very/deep/nested/path/test_example.py", 40)
        'tests/.../test_example.py'
    """
    if len(path) <= max_length:
        return path

    # Convert to Path for easier manipulation
    path_obj = Path(path)
    filename = path_obj.name
    parts = path_obj.parts

    # If even the filename is too long, truncate it
    if len(filename) >= max_length - 3:
        return "..." + filename[-(max_length - 3):]

    # Build path from start and end until we exceed max_length
    if len(parts) <= 2:
        # Very short path structure, just return as is or truncate middle
        return path if len(path) <= max_length else f"{parts[0]}/.../{filename}"

    # Start with first part and filename
    first_part = parts[0]
    truncated = f"{first_part}/.../{filename}"

    # Check if we can add more parts from the beginning
    for i in range(1, len(parts) - 1):
        test_path = "/".join(parts[:i+1]) + "/.../" + filename
        if len(test_path) <= max_length:
            truncated = test_path
        else:
            break

    return truncated


def get_terminal_width() -> int:
    """
    Get the current terminal width in columns.

    Returns:
        Terminal width in characters, defaults to 80 if unable to detect

    Examples:
        >>> width = get_terminal_width()
        >>> width > 0
        True
    """
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        return size.columns
    except Exception:
        return 80


def get_test_name_from_nodeid(nodeid: str) -> str:
    """
    Extract the test name from a pytest nodeid.

    Args:
        nodeid: Full pytest node ID like "tests/test_foo.py::test_bar"
                or "tests/test_foo.py::TestClass::test_method"

    Returns:
        Just the test name portion

    Examples:
        >>> get_test_name_from_nodeid("tests/test_foo.py::test_bar")
        'test_bar'
        >>> get_test_name_from_nodeid("tests/test_foo.py::TestClass::test_method")
        'test_method'
    """
    parts = nodeid.split("::")
    return parts[-1] if len(parts) > 1 else nodeid


def get_file_path_from_nodeid(nodeid: str) -> str:
    """
    Extract the file path from a pytest nodeid.

    Args:
        nodeid: Full pytest node ID like "tests/test_foo.py::test_bar"

    Returns:
        The file path portion

    Examples:
        >>> get_file_path_from_nodeid("tests/test_foo.py::test_bar")
        'tests/test_foo.py'
    """
    return nodeid.split("::")[0]
