"""Shared logging helpers for Podtext."""

from __future__ import annotations

import sys


def warn(message: str) -> None:
    """Display a warning message to stderr."""
    print(f"Warning: {message}", file=sys.stderr)


def error(message: str) -> None:
    """Display an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)
