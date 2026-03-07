"""Pestify: Pytest plugin for Pest-style output."""

__version__ = "0.1.0"

from pestify.reporter import PestifyTerminalReporter
from pestify.plugin import pytest_configure, pytest_report_teststatus

__all__ = [
    "__version__",
    "PestifyTerminalReporter",
    "pytest_configure",
    "pytest_report_teststatus",
]
