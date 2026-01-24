"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home(temp_dir, monkeypatch):
    """Mock HOME directory for config tests."""
    monkeypatch.setenv("HOME", str(temp_dir))
    return temp_dir


@pytest.fixture
def clean_env(monkeypatch):
    """Remove ANTHROPIC_API_KEY from environment if present."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
