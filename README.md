# Pestify

A pytest plugin that transforms test output to match [Pest PHP](https://pestphp.com/)'s beautiful aesthetic.

## Features

- **Clean, minimal output** with ✓/✗ symbols instead of dots/F/E
- **Colored results** - green for passing tests, red for failures, yellow for skipped
- **File grouping** - Tests organized by file with PASS/FAIL headers
- **Duration display** - See how long each test takes (e.g., `0.12s`)
- **Immediate failure details** - See what went wrong right away with code context
- **Zero configuration** - Just install and run `pytest` as usual
- **Standard pytest syntax** - Keep your existing `def test_*` functions

## Installation

### Using uv (recommended)

```bash
uv add --dev pestify
```

### Using pip

```bash
pip install pestify
```

## Usage

Once installed, pestify automatically transforms your pytest output. Just run:

```bash
pytest
```

That's it! No configuration needed.

### Example Output

**Before (standard pytest):**
```
=================== test session starts ===================
platform linux -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0
rootdir: /path/to/project
collected 4 items

tests/test_math.py ..                                [50%]
tests/test_user.py .F                                [100%]

======================== FAILURES =========================
_____________ test_user_validation ____________
    def test_user_validation():
>       assert user.is_valid()
E       AssertionError: assert False
...
```

**After (with pestify):**
```
  PASS  tests/test_math.py
  ✓ test_addition 0.01s
  ✓ test_subtraction 0.01s

  FAIL  tests/test_user.py
  ✓ test_user_creation 0.05s
  ⨯ test_user_validation 0.03s
  ────────────────────────────────────────
  AssertionError: assert False
    File "tests/test_user.py", line 12, in test_user_validation
  →   assert user.is_valid()

  Tests: 3 passed, 1 failed, 4 total
  Duration: 0.10s
```

## Configuration

Pestify works out of the box, but you can customize it via `pytest.ini` or `pyproject.toml`.

### pyproject.toml

```toml
[tool.pytest.ini_options]
pestify_show_context = true      # Show code context in failure output (default: true)
pestify_group_by_file = true     # Group test results by file (default: true)
pestify_show_duration = true     # Show test duration for each test (default: true)
```

### pytest.ini

```ini
[pytest]
pestify_show_context = true
pestify_group_by_file = true
pestify_show_duration = true
```

## Disabling Pestify

If you need to temporarily disable pestify and see standard pytest output:

```bash
pytest --no-pestify
```

## Verbose Mode

Pestify respects pytest's verbosity flags:

```bash
pytest -v      # More details (full file paths, more context)
pytest -vv     # Maximum details (full stack traces)
```

## Advanced Features

### Parametrized Tests

Pestify beautifully formats parametrized tests, showing each parameter set:

```
  ✓ test_math[1-2-3] 0.01s
  ✓ test_math[4-5-9] 0.01s
  ⨯ test_math[10-20-50] 0.02s
```

### Test Classes

Test classes are handled with proper nesting:

```
  PASS  tests/test_user.py
  ✓ TestUser::test_creation 0.02s
  ✓ TestUser::test_validation 0.01s
```

### Skipped and Expected Failures

Different test outcomes have distinct symbols:

- `✓` - Passed (green)
- `⨯` - Failed (red)
- `-` - Skipped (yellow)
- `x` - Expected failure (yellow)
- `X` - Unexpected pass (yellow)

### Unicode Support

If your terminal doesn't support ✓/✗ symbols, pestify automatically falls back to ASCII alternatives (`PASS`/`FAIL`).

## Compatibility

- **Python**: 3.14+
- **pytest**: 7.0.0+
- **Terminal**: Any terminal with ANSI color support
- **Parallel testing**: Compatible with pytest-xdist

## How It Works

Pestify is a pytest plugin that:

1. Registers via the `pytest11` entry point
2. Replaces pytest's default `TerminalReporter` with a custom one
3. Customizes output formatting hooks to match Pest's aesthetic
4. Uses pytest's built-in color support (no extra dependencies)

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pestify --cov-report=term-missing

# Run specific test file
pytest tests/test_reporter.py
```

### Type Checking

```bash
mypy src/pestify
```

### Linting

```bash
ruff check src/pestify
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

Inspired by [Pest PHP](https://pestphp.com/) by Nuno Maduro and contributors.

## Changelog

### 0.1.0 (2025)

- Initial release
- Core features: file grouping, colored output, duration display
- Configuration options
- Full pytest integration
- Comprehensive test coverage
