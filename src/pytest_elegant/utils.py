"""Helper utility functions for pytest-elegant."""

import os
import shutil
import sys
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


def supports_unicode() -> bool:
    """
    Check if the terminal supports Unicode characters.

    Returns:
        True if Unicode is supported, False otherwise

    Examples:
        >>> supports_unicode()  # doctest: +SKIP
        True
    """
    # Check encoding
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return False

    # Common encodings that support Unicode
    unicode_encodings = ["utf-8", "utf8", "utf-16", "utf-32"]
    if encoding.lower() in unicode_encodings:
        return True

    # Try to encode test characters
    try:
        "✓✗⨯".encode(encoding)
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


def get_symbols(use_unicode: bool = True) -> dict[str, str]:
    """
    Get appropriate symbols based on terminal capabilities.

    Args:
        use_unicode: Whether to use Unicode symbols (auto-detected if True)

    Returns:
        Dictionary mapping outcome types to symbols

    Examples:
        >>> symbols = get_symbols(use_unicode=False)
        >>> symbols['passed']
        '.'
        >>> symbols = get_symbols(use_unicode=True)  # doctest: +SKIP
        >>> symbols['passed']  # doctest: +SKIP
        '✓'
    """
    if use_unicode and supports_unicode():
        return {
            "passed": "✓",
            "failed": "⨯",
            "skipped": "-",
            "xfailed": "x",
            "xpassed": "X",
            "error": "E",
        }
    else:
        # ASCII fallback
        return {
            "passed": ".",
            "failed": "F",
            "skipped": "s",
            "xfailed": "x",
            "xpassed": "X",
            "error": "E",
        }


def truncate_test_name(test_name: str, max_length: int = 80) -> str:
    """
    Truncate long test names intelligently.

    Preserves important parts like test name and parameters.

    Args:
        test_name: The test name to truncate
        max_length: Maximum length of the returned name

    Returns:
        Truncated test name string

    Examples:
        >>> truncate_test_name("test_very_long_function_name_with_many_words", 30)
        'test_very_long_func...ds'
        >>> truncate_test_name("test_foo[param1-param2]", 50)
        'test_foo[param1-param2]'
    """
    if len(test_name) <= max_length:
        return test_name

    # Check if this is a parametrized test (has brackets)
    if "[" in test_name and "]" in test_name:
        # Split into name and parameters
        base_name, params = test_name.split("[", 1)
        params = "[" + params

        # Calculate space available for base name
        available = max_length - len(params) - 3  # 3 for "..."

        if available < 10:
            # Not enough space, truncate the whole thing
            return test_name[:max_length - 3] + "..."

        # Truncate base name and keep params
        return base_name[:available] + "..." + params
    else:
        # No parameters, just truncate with ellipsis in middle
        # Keep beginning and end
        if max_length < 10:
            return test_name[:max_length]

        keep_start = (max_length - 3) // 2
        keep_end = max_length - 3 - keep_start
        return test_name[:keep_start] + "..." + test_name[-keep_end:]


def extract_test_parts(nodeid: str) -> tuple[str, str, str | None, str | None]:
    """
    Extract all parts from a pytest nodeid.

    Args:
        nodeid: Full pytest node ID

    Returns:
        Tuple of (file_path, test_name, class_name, parameters)

    Examples:
        >>> extract_test_parts("tests/test_foo.py::test_bar")
        ('tests/test_foo.py', 'test_bar', None, None)
        >>> extract_test_parts("tests/test_foo.py::TestClass::test_method")
        ('tests/test_foo.py', 'test_method', 'TestClass', None)
        >>> extract_test_parts("tests/test_foo.py::test_bar[param1-param2]")
        ('tests/test_foo.py', 'test_bar', None, 'param1-param2')
        >>> extract_test_parts("tests/test_foo.py::TestClass::test_method[1-2]")
        ('tests/test_foo.py', 'test_method', 'TestClass', '1-2')
    """
    # Split by ::
    parts = nodeid.split("::")
    file_path = parts[0]

    if len(parts) == 1:
        return (file_path, nodeid, None, None)

    # Check for parametrized test (contains [])
    parameters = None
    if "[" in parts[-1] and "]" in parts[-1]:
        test_name, params = parts[-1].split("[", 1)
        parameters = params.rstrip("]")
    else:
        test_name = parts[-1]

    # Check for class (3 parts: file::Class::method)
    class_name = None
    if len(parts) == 3:
        class_name = parts[1]

    return (file_path, test_name, class_name, parameters)


def format_test_name(test_name: str) -> str:
    """
    Format a test function name into human-readable format.

    Removes 'test_' prefix and converts underscores to spaces.

    Args:
        test_name: Raw test function name (e.g., 'test_it_extracts_request')

    Returns:
        Formatted test name (e.g., 'it extracts request')

    Examples:
        >>> format_test_name('test_it_extracts_request')
        'it extracts request'
        >>> format_test_name('test_addition')
        'addition'
        >>> format_test_name('test_user_can_login')
        'user can login'
        >>> format_test_name('some_test_without_prefix')
        'some test without prefix'
    """
    # Remove 'test_' prefix if present
    if test_name.startswith("test_"):
        test_name = test_name[5:]  # Remove 'test_'

    # Replace underscores with spaces
    return test_name.replace("_", " ")
