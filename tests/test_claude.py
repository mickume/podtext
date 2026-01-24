"""Tests for Claude API integration and prompt loading.

Feature: podtext
Property tests verify universal properties across generated inputs.
"""

import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from podtext.claude import (
    ClaudeAPIError,
    ClaudeClient,
    analyze_with_fallback,
    create_claude_client,
)
from podtext.prompts import (
    DEFAULT_PROMPTS,
    Prompts,
    _parse_prompts_markdown,
    create_default_prompts_file,
    load_prompts,
)


class TestPromptRuntimeLoading:
    """
    Property 13: Prompt Runtime Loading

    For any modification to the prompts markdown file,
    subsequent Claude API calls SHALL use the updated prompt content.

    Validates: Requirements 9.2
    """

    @settings(max_examples=100)
    @given(
        custom_ad_prompt=st.text(
            min_size=10,
            max_size=200,
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,:{}\n",
        ),
    )
    def test_prompts_loaded_from_file_at_runtime(self, custom_ad_prompt: str) -> None:
        """Property 13: Modified prompts file is used for subsequent calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir) / "prompts.md"

            # Create prompts file with custom content
            prompts_content = f"""# Advertisement Detection

{custom_ad_prompt}

# Content Summary

Summarize this: {{text}}

# Topic Extraction

Extract topics: {{text}}

# Keyword Extraction

Extract keywords: {{text}}
"""
            prompts_path.write_text(prompts_content, encoding="utf-8")

            # Load prompts
            prompts = load_prompts(prompts_path)

            # Verify custom prompt was loaded (strip to handle whitespace normalization)
            assert custom_ad_prompt.strip() in prompts.advertisement_detection, (
                f"Custom prompt should be loaded, got: {prompts.advertisement_detection}"
            )

    def test_modified_file_affects_subsequent_loads(self) -> None:
        """Modifying the prompts file should affect subsequent loads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir) / "prompts.md"

            # Create initial prompts file
            initial_content = """# Advertisement Detection

Initial ad detection prompt {text}

# Content Summary

Initial summary prompt {text}

# Topic Extraction

Initial topics prompt {text}

# Keyword Extraction

Initial keywords prompt {text}
"""
            prompts_path.write_text(initial_content, encoding="utf-8")

            # First load
            prompts1 = load_prompts(prompts_path)
            assert "Initial ad detection" in prompts1.advertisement_detection

            # Modify file
            modified_content = """# Advertisement Detection

Modified ad detection prompt {text}

# Content Summary

Modified summary prompt {text}

# Topic Extraction

Modified topics prompt {text}

# Keyword Extraction

Modified keywords prompt {text}
"""
            prompts_path.write_text(modified_content, encoding="utf-8")

            # Second load
            prompts2 = load_prompts(prompts_path)
            assert "Modified ad detection" in prompts2.advertisement_detection


class TestPromptsFallback:
    """Tests for prompts fallback behavior."""

    def test_missing_file_uses_defaults(self) -> None:
        """Missing prompts file should use defaults with warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir) / "nonexistent" / "prompts.md"

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                prompts = load_prompts(prompts_path)

                # Should warn about missing file
                assert len(w) == 1
                assert "not found" in str(w[0].message).lower()

            # Should return defaults
            assert prompts.advertisement_detection == DEFAULT_PROMPTS.advertisement_detection

    def test_malformed_file_uses_defaults(self) -> None:
        """Malformed prompts file should use defaults with warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir) / "prompts.md"

            # Write malformed content (missing sections)
            prompts_path.write_text("This is not a valid prompts file", encoding="utf-8")

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                prompts = load_prompts(prompts_path)

                # Should warn about malformed file
                assert len(w) == 1
                assert "malformed" in str(w[0].message).lower()

            # Should return defaults
            assert prompts.content_summary == DEFAULT_PROMPTS.content_summary


class TestPromptParsing:
    """Tests for prompt markdown parsing."""

    def test_parse_valid_prompts_markdown(self) -> None:
        """Valid prompts markdown should parse correctly."""
        content = """# Advertisement Detection

Ad prompt here {text}

# Content Summary

Summary prompt {text}

# Topic Extraction

Topics prompt {text}

# Keyword Extraction

Keywords prompt {text}
"""
        result = _parse_prompts_markdown(content)

        assert result is not None
        assert "Ad prompt here" in result.advertisement_detection
        assert "Summary prompt" in result.content_summary
        assert "Topics prompt" in result.topic_extraction
        assert "Keywords prompt" in result.keyword_extraction

    def test_parse_missing_section_returns_none(self) -> None:
        """Missing required section should return None."""
        content = """# Advertisement Detection

Ad prompt here {text}

# Content Summary

Summary prompt {text}
"""
        # Missing Topic Extraction and Keyword Extraction
        result = _parse_prompts_markdown(content)
        assert result is None


class TestCreateDefaultPromptsFile:
    """Tests for default prompts file creation."""

    def test_create_default_prompts_file(self) -> None:
        """Should create prompts file with default content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir) / "subdir" / "prompts.md"

            result = create_default_prompts_file(prompts_path)

            assert result == prompts_path
            assert prompts_path.exists()

            # Should be parseable
            prompts = load_prompts(prompts_path)
            assert prompts.advertisement_detection


class TestClaudeClientCreation:
    """Tests for Claude client creation."""

    def test_create_client_with_api_key(self) -> None:
        """Should create client when API key provided."""
        client = create_claude_client("test-api-key")
        assert client is not None
        assert client.api_key == "test-api-key"

    def test_create_client_without_api_key(self) -> None:
        """Should return None when no API key."""
        client = create_claude_client(None)
        assert client is None

        client = create_claude_client("")
        assert client is None


class TestClaudeClientAnalysis:
    """Tests for Claude client analysis methods."""

    def test_detect_advertisements_parses_response(self) -> None:
        """Should parse advertisement detection response correctly."""
        mock_anthropic = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"advertisements": [{"start": 100, "end": 200, "confidence": "high"}]}')]
        mock_anthropic.messages.create.return_value = mock_message

        client = ClaudeClient(
            api_key="test-key",
            _client=mock_anthropic,
            _prompts=DEFAULT_PROMPTS,
        )

        result = client.detect_advertisements("Test transcript")

        assert len(result) == 1
        assert result[0] == (100, 200)

    def test_detect_advertisements_filters_low_confidence(self) -> None:
        """Should filter out low confidence advertisements."""
        mock_anthropic = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='''{
            "advertisements": [
                {"start": 100, "end": 200, "confidence": "high"},
                {"start": 300, "end": 400, "confidence": "low"}
            ]
        }''')]
        mock_anthropic.messages.create.return_value = mock_message

        client = ClaudeClient(
            api_key="test-key",
            _client=mock_anthropic,
            _prompts=DEFAULT_PROMPTS,
        )

        result = client.detect_advertisements("Test transcript")

        assert len(result) == 1
        assert result[0] == (100, 200)

    def test_extract_topics_parses_json_array(self) -> None:
        """Should parse topics from JSON array."""
        mock_anthropic = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='["Topic 1: Description", "Topic 2: Another"]')]
        mock_anthropic.messages.create.return_value = mock_message

        client = ClaudeClient(
            api_key="test-key",
            _client=mock_anthropic,
            _prompts=DEFAULT_PROMPTS,
        )

        result = client.extract_topics("Test transcript")

        assert len(result) == 2
        assert "Topic 1" in result[0]

    def test_extract_keywords_limits_to_20(self) -> None:
        """Should limit keywords to 20."""
        mock_anthropic = MagicMock()
        keywords = [f"keyword{i}" for i in range(30)]
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=str(keywords).replace("'", '"'))]
        mock_anthropic.messages.create.return_value = mock_message

        client = ClaudeClient(
            api_key="test-key",
            _client=mock_anthropic,
            _prompts=DEFAULT_PROMPTS,
        )

        result = client.extract_keywords("Test transcript")

        assert len(result) <= 20


class TestAnalyzeWithFallback:
    """Tests for graceful fallback when Claude unavailable."""

    def test_no_api_key_returns_none_with_warning(self) -> None:
        """Should return None with warning when no API key."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            result = analyze_with_fallback("Test text", None)

            assert result is None
            assert len(w) == 1
            assert "not configured" in str(w[0].message).lower()

    @patch("podtext.claude.ClaudeClient")
    def test_api_error_returns_none_with_warning(self, mock_client_class: MagicMock) -> None:
        """Should return None with warning when API fails."""
        mock_client = MagicMock()
        mock_client.analyze_content.side_effect = ClaudeAPIError("API Error")
        mock_client_class.return_value = mock_client

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            result = analyze_with_fallback("Test text", "test-key")

            assert result is None
            assert len(w) == 1
            assert "unavailable" in str(w[0].message).lower()


class TestClaudeClientPromptReload:
    """Tests for prompt reloading."""

    def test_reload_prompts_updates_client(self) -> None:
        """reload_prompts should update the client's prompts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_path = Path(tmpdir) / "prompts.md"

            # Create initial prompts
            create_default_prompts_file(prompts_path)

            mock_anthropic = MagicMock()

            with patch("podtext.claude.load_prompts") as mock_load:
                mock_load.return_value = DEFAULT_PROMPTS

                client = ClaudeClient(
                    api_key="test-key",
                    _client=mock_anthropic,
                )

                # Modify mock to return different prompts
                new_prompts = Prompts(
                    advertisement_detection="New ad prompt",
                    content_summary="New summary",
                    topic_extraction="New topics",
                    keyword_extraction="New keywords",
                )
                mock_load.return_value = new_prompts

                client.reload_prompts()

                assert client.prompts.advertisement_detection == "New ad prompt"
