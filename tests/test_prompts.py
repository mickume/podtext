"""Unit tests for the Prompt Loader.

Tests prompt loading from markdown files, fallback to defaults,
and warning display.

Requirements: 9.1, 9.2, 9.3
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest

from podtext.core.prompts import (
    DEFAULT_ADVERTISEMENT_DETECTION_PROMPT,
    DEFAULT_CONTENT_SUMMARY_PROMPT,
    DEFAULT_KEYWORD_EXTRACTION_PROMPT,
    DEFAULT_TOPIC_EXTRACTION_PROMPT,
    Prompts,
    _parse_prompts_markdown,
    generate_default_prompts_markdown,
    load_prompts,
)


@pytest.fixture
def temp_prompts_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for prompts files."""
    yield tmp_path


class TestPromptsDataclass:
    """Tests for the Prompts dataclass."""

    def test_prompts_defaults(self) -> None:
        """Test that Prompts has correct default values."""
        prompts = Prompts()

        assert prompts.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT
        assert prompts.content_summary == DEFAULT_CONTENT_SUMMARY_PROMPT
        assert prompts.topic_extraction == DEFAULT_TOPIC_EXTRACTION_PROMPT
        assert prompts.keyword_extraction == DEFAULT_KEYWORD_EXTRACTION_PROMPT

    def test_prompts_defaults_classmethod(self) -> None:
        """Test the defaults() classmethod."""
        prompts = Prompts.defaults()

        assert prompts.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT
        assert prompts.content_summary == DEFAULT_CONTENT_SUMMARY_PROMPT
        assert prompts.topic_extraction == DEFAULT_TOPIC_EXTRACTION_PROMPT
        assert prompts.keyword_extraction == DEFAULT_KEYWORD_EXTRACTION_PROMPT

    def test_prompts_custom_values(self) -> None:
        """Test creating Prompts with custom values."""
        prompts = Prompts(
            advertisement_detection="Custom ad prompt",
            content_summary="Custom summary prompt",
            topic_extraction="Custom topic prompt",
            keyword_extraction="Custom keyword prompt",
        )

        assert prompts.advertisement_detection == "Custom ad prompt"
        assert prompts.content_summary == "Custom summary prompt"
        assert prompts.topic_extraction == "Custom topic prompt"
        assert prompts.keyword_extraction == "Custom keyword prompt"


class TestParsePromptsMarkdown:
    """Tests for markdown parsing."""

    def test_parse_all_sections(self) -> None:
        """Test parsing markdown with all sections."""
        content = """# Advertisement Detection

Custom ad detection prompt here.

# Content Summary

Custom summary prompt here.

# Topic Extraction

Custom topic prompt here.

# Keyword Extraction

Custom keyword prompt here.
"""
        result = _parse_prompts_markdown(content)

        assert result["advertisement_detection"] == "Custom ad detection prompt here."
        assert result["content_summary"] == "Custom summary prompt here."
        assert result["topic_extraction"] == "Custom topic prompt here."
        assert result["keyword_extraction"] == "Custom keyword prompt here."

    def test_parse_partial_sections(self) -> None:
        """Test parsing markdown with only some sections."""
        content = """# Advertisement Detection

Custom ad detection prompt.

# Content Summary

Custom summary prompt.
"""
        result = _parse_prompts_markdown(content)

        assert "advertisement_detection" in result
        assert "content_summary" in result
        assert "topic_extraction" not in result
        assert "keyword_extraction" not in result

    def test_parse_empty_content(self) -> None:
        """Test parsing empty markdown content."""
        result = _parse_prompts_markdown("")

        assert result == {}

    def test_parse_no_valid_sections(self) -> None:
        """Test parsing markdown with no valid sections."""
        content = """# Some Other Header

Some content here.

# Another Header

More content.
"""
        result = _parse_prompts_markdown(content)

        assert result == {}

    def test_parse_multiline_prompts(self) -> None:
        """Test parsing prompts with multiple lines."""
        content = """# Advertisement Detection

Line 1 of the prompt.
Line 2 of the prompt.
Line 3 of the prompt.

# Content Summary

Summary line 1.
Summary line 2.
"""
        result = _parse_prompts_markdown(content)

        assert "Line 1" in result["advertisement_detection"]
        assert "Line 2" in result["advertisement_detection"]
        assert "Line 3" in result["advertisement_detection"]

    def test_parse_case_insensitive_headers(self) -> None:
        """Test that header matching is case-insensitive."""
        content = """# ADVERTISEMENT DETECTION

Ad prompt.

# content summary

Summary prompt.
"""
        result = _parse_prompts_markdown(content)

        assert "advertisement_detection" in result
        assert "content_summary" in result


class TestLoadPrompts:
    """Tests for loading prompts from files.

    Validates: Requirements 9.1, 9.2, 9.3
    """

    def test_load_prompts_no_file_creates_default_in_global(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test that missing prompts file creates default in global location when local .podtext doesn't exist.

        Validates: Requirements 9.3
        """
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        # Should use defaults
        assert prompts.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT
        assert prompts.content_summary == DEFAULT_CONTENT_SUMMARY_PROMPT

        # Should create the global prompts file (since local .podtext doesn't exist)
        assert global_path.exists()
        assert not local_path.exists()
        content = global_path.read_text(encoding='utf-8')
        assert "# Advertisement Detection" in content
        assert "# Content Summary" in content

    def test_load_prompts_no_file_creates_default_in_local_when_exists(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test that missing prompts file creates default in local location when .podtext exists.

        Validates: Requirements 9.3
        """
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        
        # Create the local .podtext directory
        local_path.parent.mkdir(parents=True)

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        # Should use defaults
        assert prompts.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT
        assert prompts.content_summary == DEFAULT_CONTENT_SUMMARY_PROMPT

        # Should create the local prompts file (since local .podtext exists)
        assert local_path.exists()
        assert not global_path.exists()
        content = local_path.read_text(encoding='utf-8')
        assert "# Advertisement Detection" in content
        assert "# Content Summary" in content

    def test_load_prompts_no_file_no_warning(
        self, temp_prompts_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that no warning is displayed when file is auto-created."""
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"

        load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=False,
        )

        # Should not display warning (file is auto-created now)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_load_prompts_from_local_file(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test loading prompts from local file.

        Validates: Requirements 9.2
        """
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        local_path.parent.mkdir(parents=True)

        local_path.write_text("""# Advertisement Detection

Local ad prompt.

# Content Summary

Local summary prompt.

# Topic Extraction

Local topic prompt.

# Keyword Extraction

Local keyword prompt.
""")

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        assert prompts.advertisement_detection == "Local ad prompt."
        assert prompts.content_summary == "Local summary prompt."
        assert prompts.topic_extraction == "Local topic prompt."
        assert prompts.keyword_extraction == "Local keyword prompt."

    def test_load_prompts_from_global_file(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test loading prompts from global file when local doesn't exist.

        Validates: Requirements 9.2
        """
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""# Advertisement Detection

Global ad prompt.

# Content Summary

Global summary prompt.

# Topic Extraction

Global topic prompt.

# Keyword Extraction

Global keyword prompt.
""")

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        assert prompts.advertisement_detection == "Global ad prompt."
        assert prompts.content_summary == "Global summary prompt."

    def test_local_file_takes_priority_over_global(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test that local prompts file takes priority over global."""
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        local_path.parent.mkdir(parents=True)
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""# Advertisement Detection

Global ad prompt.
""")

        local_path.write_text("""# Advertisement Detection

Local ad prompt.
""")

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        assert prompts.advertisement_detection == "Local ad prompt."

    def test_load_prompts_partial_file_uses_defaults_for_missing(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test that missing sections use defaults."""
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        local_path.parent.mkdir(parents=True)

        # Only include some sections
        local_path.write_text("""# Advertisement Detection

Custom ad prompt.
""")

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        # Custom value for specified section
        assert prompts.advertisement_detection == "Custom ad prompt."
        # Defaults for missing sections
        assert prompts.content_summary == DEFAULT_CONTENT_SUMMARY_PROMPT
        assert prompts.topic_extraction == DEFAULT_TOPIC_EXTRACTION_PROMPT
        assert prompts.keyword_extraction == DEFAULT_KEYWORD_EXTRACTION_PROMPT

    def test_load_prompts_malformed_file_uses_defaults(
        self, temp_prompts_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that malformed file falls back to defaults with warning.

        Validates: Requirements 9.3
        """
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        local_path.parent.mkdir(parents=True)

        # Write file with no valid sections
        local_path.write_text("""This is not a valid prompts file.
It has no proper headers.
Just random text.
""")

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        # Should use defaults
        assert prompts.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT

        # Should display warning
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "malformed" in captured.err

    def test_load_prompts_empty_file_uses_defaults(
        self, temp_prompts_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that empty file falls back to defaults with warning."""
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        local_path.parent.mkdir(parents=True)

        local_path.write_text("")

        prompts = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=True,
        )

        # Should use defaults
        assert prompts.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT

        # Should display warning
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestGenerateDefaultPromptsMarkdown:
    """Tests for generating default prompts markdown."""

    def test_generate_contains_all_sections(self) -> None:
        """Test that generated markdown contains all sections."""
        content = generate_default_prompts_markdown()

        assert "# Advertisement Detection" in content
        assert "# Content Summary" in content
        assert "# Topic Extraction" in content
        assert "# Keyword Extraction" in content

    def test_generate_contains_default_prompts(self) -> None:
        """Test that generated markdown contains default prompt content."""
        content = generate_default_prompts_markdown()

        # Check for key phrases from default prompts
        assert "advertising sections" in content
        assert "Summarize" in content
        assert "main topics" in content
        assert "keywords" in content

    def test_generated_markdown_is_parseable(self) -> None:
        """Test that generated markdown can be parsed back."""
        content = generate_default_prompts_markdown()
        result = _parse_prompts_markdown(content)

        assert "advertisement_detection" in result
        assert "content_summary" in result
        assert "topic_extraction" in result
        assert "keyword_extraction" in result


class TestRuntimeLoading:
    """Tests for runtime prompt loading behavior.

    Validates: Requirements 9.2 - prompts loaded at runtime
    """

    def test_prompts_loaded_fresh_each_call(
        self, temp_prompts_dir: Path
    ) -> None:
        """Test that prompts are loaded fresh on each call."""
        local_path = temp_prompts_dir / "local" / "prompts.md"
        global_path = temp_prompts_dir / "global" / "prompts.md"
        local_path.parent.mkdir(parents=True)

        # First version
        local_path.write_text("""# Advertisement Detection

Version 1 prompt.
""")

        prompts1 = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=False,
        )
        assert prompts1.advertisement_detection == "Version 1 prompt."

        # Update the file
        local_path.write_text("""# Advertisement Detection

Version 2 prompt.
""")

        # Load again - should get new content
        prompts2 = load_prompts(
            local_path=local_path,
            global_path=global_path,
            warn_on_fallback=False,
        )
        assert prompts2.advertisement_detection == "Version 2 prompt."
