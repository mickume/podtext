"""Tests for prompt management.

Feature: podtext
Property 13: Prompt Runtime Loading
"""

import pytest
import warnings
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path

from podtext.prompts import (
    load_prompts,
    get_prompt,
    _parse_prompts_markdown,
    DEFAULT_PROMPTS,
)


class TestParsePromptsMarkdown:
    """Tests for markdown parsing."""

    def test_parse_single_section(self):
        """Parse single section from markdown."""
        content = """\
# Test Section

This is the prompt content.
"""
        result = _parse_prompts_markdown(content)
        assert "test_section" in result
        assert result["test_section"] == "This is the prompt content."

    def test_parse_multiple_sections(self):
        """Parse multiple sections from markdown."""
        content = """\
# First Section

First prompt.

# Second Section

Second prompt.
"""
        result = _parse_prompts_markdown(content)
        assert len(result) == 2
        assert "first_section" in result
        assert "second_section" in result

    def test_parse_empty_content(self):
        """Parse empty content returns empty dict."""
        result = _parse_prompts_markdown("")
        assert result == {}

    def test_parse_no_headers(self):
        """Parse content without headers returns empty dict."""
        content = "Just some text without headers"
        result = _parse_prompts_markdown(content)
        assert result == {}


class TestLoadPrompts:
    """Tests for loading prompts."""

    def test_load_returns_defaults_when_file_missing(self, temp_dir, monkeypatch):
        """Load returns defaults when file is missing."""
        monkeypatch.chdir(temp_dir)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            prompts = load_prompts()

            assert len(w) == 1
            assert "not found" in str(w[0].message)

        assert prompts == DEFAULT_PROMPTS

    def test_load_from_file(self, temp_dir, monkeypatch):
        """Load prompts from file."""
        monkeypatch.chdir(temp_dir)

        prompts_dir = temp_dir / ".podtext"
        prompts_dir.mkdir()
        prompts_file = prompts_dir / "prompts.md"
        prompts_file.write_text("""\
# Custom Prompt

This is a custom prompt.
""")

        prompts = load_prompts()

        assert "custom_prompt" in prompts
        assert prompts["custom_prompt"] == "This is a custom prompt."

    def test_load_merges_with_defaults(self, temp_dir, monkeypatch):
        """Custom prompts are merged with defaults."""
        monkeypatch.chdir(temp_dir)

        prompts_dir = temp_dir / ".podtext"
        prompts_dir.mkdir()
        prompts_file = prompts_dir / "prompts.md"
        prompts_file.write_text("""\
# Content Summary

Custom summary prompt.
""")

        prompts = load_prompts()

        # Custom prompt should override
        assert "content_summary" in prompts
        assert prompts["content_summary"] == "Custom summary prompt."

        # Default prompts should still be available
        assert "advertisement_detection" in prompts

    def test_load_malformed_file_returns_defaults(self, temp_dir, monkeypatch):
        """Malformed file returns defaults with warning."""
        monkeypatch.chdir(temp_dir)

        prompts_dir = temp_dir / ".podtext"
        prompts_dir.mkdir()
        prompts_file = prompts_dir / "prompts.md"
        prompts_file.write_text("No headers, just text")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            prompts = load_prompts()

            assert len(w) == 1
            assert "malformed" in str(w[0].message)

        assert prompts == DEFAULT_PROMPTS


class TestGetPrompt:
    """Tests for getting individual prompts."""

    def test_get_existing_prompt(self):
        """Get an existing prompt."""
        prompts = {"test": "Hello {user}!"}
        result = get_prompt("test", prompts, user="World")
        assert result == "Hello World!"

    def test_get_nonexistent_prompt(self):
        """Get nonexistent prompt returns empty with warning."""
        prompts = {}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = get_prompt("nonexistent", prompts)

            assert len(w) == 1
            assert "not found" in str(w[0].message)

        assert result == ""


class TestProperty13PromptRuntimeLoading:
    """Property 13: Prompt Runtime Loading.

    For any modification to the prompts markdown file,
    subsequent Claude API calls SHALL use the updated prompt content.

    Validates: Requirements 9.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        prompt_content=st.text(
            min_size=5, max_size=100,
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"), blacklist_characters="#\x00")
        ),
    )
    def test_prompts_reflect_file_changes(self, temp_dir, monkeypatch, prompt_content):
        """Prompts are reloaded from file on each call."""
        monkeypatch.chdir(temp_dir)

        prompts_dir = temp_dir / ".podtext"
        prompts_dir.mkdir(exist_ok=True)
        prompts_file = prompts_dir / "prompts.md"

        # Write initial content
        prompts_file.write_text(f"""\
# Dynamic Prompt

{prompt_content}
""")

        # Load prompts
        prompts = load_prompts()

        # Verify the content matches
        assert prompts["dynamic_prompt"] == prompt_content

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        content1=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="#")),
        content2=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="#")),
    )
    def test_file_update_changes_loaded_prompts(self, temp_dir, monkeypatch, content1, content2):
        """Updating file between loads changes the prompts."""
        monkeypatch.chdir(temp_dir)

        prompts_dir = temp_dir / ".podtext"
        prompts_dir.mkdir(exist_ok=True)
        prompts_file = prompts_dir / "prompts.md"

        # Write first version
        prompts_file.write_text(f"# Test Prompt\n\n{content1}")
        prompts1 = load_prompts()

        # Write second version
        prompts_file.write_text(f"# Test Prompt\n\n{content2}")
        prompts2 = load_prompts()

        # Each load should reflect the file content at that time
        assert prompts1["test_prompt"] == content1
        assert prompts2["test_prompt"] == content2
