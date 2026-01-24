"""Tests for Claude API client.

Feature: podtext
"""

import pytest
import warnings
from unittest.mock import MagicMock, patch
import json

from podtext.claude import (
    detect_advertisements,
    analyze_content,
    _parse_json_array,
    _clear_prompts_cache,
)
from podtext.models import AnalysisResult


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear prompts cache before each test."""
    _clear_prompts_cache()
    yield
    _clear_prompts_cache()


class TestParseJsonArray:
    """Tests for JSON array parsing helper."""

    def test_parse_valid_array(self):
        """Parse valid JSON array."""
        text = '["item1", "item2", "item3"]'
        result = _parse_json_array(text)
        assert result == ["item1", "item2", "item3"]

    def test_parse_array_in_text(self):
        """Parse JSON array embedded in text."""
        text = 'Here are the results: ["a", "b", "c"] and that is all.'
        result = _parse_json_array(text)
        assert result == ["a", "b", "c"]

    def test_parse_invalid_json(self):
        """Invalid JSON returns empty list."""
        text = "This is not JSON"
        result = _parse_json_array(text)
        assert result == []

    def test_parse_empty_array(self):
        """Parse empty JSON array."""
        text = "[]"
        result = _parse_json_array(text)
        assert result == []


class TestDetectAdvertisements:
    """Tests for advertisement detection."""

    def test_no_api_key_returns_empty(self):
        """No API key returns empty list with warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = detect_advertisements("test text", "")

            assert len(w) == 1
            assert "No API key" in str(w[0].message)

        assert result == []

    @patch("podtext.claude._create_client")
    def test_successful_detection(self, mock_create_client):
        """Successful advertisement detection."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='[{"start": 100, "end": 200, "confidence": "high"}]')]
        mock_client.messages.create.return_value = mock_response

        result = detect_advertisements("test text", "test-api-key")

        assert result == [(100, 200)]

    @patch("podtext.claude._create_client")
    def test_filters_low_confidence(self, mock_create_client):
        """Low confidence ads are filtered out."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='''[
            {"start": 100, "end": 200, "confidence": "high"},
            {"start": 300, "end": 400, "confidence": "low"}
        ]''')]
        mock_client.messages.create.return_value = mock_response

        result = detect_advertisements("test text", "test-api-key")

        assert result == [(100, 200)]

    @patch("podtext.claude._create_client")
    def test_api_error_returns_empty(self, mock_create_client):
        """API error returns empty list with warning."""
        import anthropic
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="API Error",
            request=MagicMock(),
            body=None
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = detect_advertisements("test text", "test-api-key")

            assert any("API error" in str(warning.message) for warning in w)

        assert result == []


class TestAnalyzeContent:
    """Tests for content analysis."""

    def test_no_api_key_returns_empty_result(self):
        """No API key returns empty AnalysisResult with warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = analyze_content("test text", "")

            assert len(w) == 1
            assert "No API key" in str(w[0].message)

        assert isinstance(result, AnalysisResult)
        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []

    @patch("podtext.claude._create_client")
    def test_successful_analysis(self, mock_create_client):
        """Successful content analysis."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Mock responses for summary, topics, and keywords
        mock_responses = [
            MagicMock(content=[MagicMock(text="This is a summary.")]),
            MagicMock(content=[MagicMock(text='["Topic 1", "Topic 2"]')]),
            MagicMock(content=[MagicMock(text='["keyword1", "keyword2"]')]),
        ]
        mock_client.messages.create.side_effect = mock_responses

        result = analyze_content("test text", "test-api-key")

        assert isinstance(result, AnalysisResult)
        assert result.summary == "This is a summary."
        assert result.topics == ["Topic 1", "Topic 2"]
        assert result.keywords == ["keyword1", "keyword2"]

    @patch("podtext.claude._create_client")
    def test_api_error_returns_empty_result(self, mock_create_client):
        """API error returns empty AnalysisResult with warning."""
        import anthropic
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.APIError(
            message="API Error",
            request=MagicMock(),
            body=None
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = analyze_content("test text", "test-api-key")

            assert any("API error" in str(warning.message) for warning in w)

        assert isinstance(result, AnalysisResult)
        assert result.summary == ""
