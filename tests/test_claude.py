"""Unit tests for the Claude API Client.

Tests advertisement detection, content analysis, and API unavailability handling.

Requirements: 6.1, 6.4, 7.1
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from anthropic import APIConnectionError, APIError, AuthenticationError

from podtext.core.prompts import Prompts
from podtext.services.claude import (
    AnalysisResult,
    ClaudeAPIError,
    ClaudeAPIUnavailableError,
    _parse_advertisement_response,
    _parse_keywords_response,
    _parse_topics_response,
    analyze_content,
    detect_advertisements,
    detect_advertisements_safe,
)


class TestAnalysisResultDataclass:
    """Tests for the AnalysisResult dataclass."""

    def test_default_values(self) -> None:
        """Test that AnalysisResult has correct default values."""
        result = AnalysisResult()

        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []
        assert result.ad_markers == []

    def test_custom_values(self) -> None:
        """Test creating AnalysisResult with custom values."""
        result = AnalysisResult(
            summary="Test summary",
            topics=["Topic 1", "Topic 2"],
            keywords=["keyword1", "keyword2"],
            ad_markers=[(0, 100), (200, 300)],
        )

        assert result.summary == "Test summary"
        assert result.topics == ["Topic 1", "Topic 2"]
        assert result.keywords == ["keyword1", "keyword2"]
        assert result.ad_markers == [(0, 100), (200, 300)]


class TestParseAdvertisementResponse:
    """Tests for parsing advertisement detection responses."""

    def test_parse_valid_response(self) -> None:
        """Test parsing a valid JSON response."""
        response = '''
        {
            "advertisements": [
                {"start": 0, "end": 100, "confidence": 0.95},
                {"start": 500, "end": 600, "confidence": 0.85}
            ]
        }
        '''
        result = _parse_advertisement_response(response)

        assert result == [(0, 100), (500, 600)]

    def test_parse_response_with_surrounding_text(self) -> None:
        """Test parsing JSON embedded in explanation text."""
        response = '''
        Here are the advertisements I found:
        {
            "advertisements": [
                {"start": 100, "end": 200, "confidence": 0.9}
            ]
        }
        Let me know if you need more details.
        '''
        result = _parse_advertisement_response(response)

        assert result == [(100, 200)]

    def test_filter_low_confidence(self) -> None:
        """Test that low confidence advertisements are filtered out."""
        response = '''
        {
            "advertisements": [
                {"start": 0, "end": 100, "confidence": 0.95},
                {"start": 200, "end": 300, "confidence": 0.5},
                {"start": 400, "end": 500, "confidence": 0.79}
            ]
        }
        '''
        result = _parse_advertisement_response(response)

        # Only the first one has confidence >= 0.8
        assert result == [(0, 100)]

    def test_parse_empty_advertisements(self) -> None:
        """Test parsing response with no advertisements."""
        response = '{"advertisements": []}'
        result = _parse_advertisement_response(response)

        assert result == []

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON returns empty list."""
        response = "This is not JSON"
        result = _parse_advertisement_response(response)

        assert result == []

    def test_parse_no_json(self) -> None:
        """Test parsing response with no JSON returns empty list."""
        response = "I couldn't find any advertisements in the text."
        result = _parse_advertisement_response(response)

        assert result == []

    def test_parse_invalid_positions(self) -> None:
        """Test that invalid positions are filtered out."""
        response = '''
        {
            "advertisements": [
                {"start": -1, "end": 100, "confidence": 0.9},
                {"start": 100, "end": 50, "confidence": 0.9},
                {"start": "invalid", "end": 100, "confidence": 0.9},
                {"start": 200, "end": 300, "confidence": 0.9}
            ]
        }
        '''
        result = _parse_advertisement_response(response)

        # Only the last one is valid
        assert result == [(200, 300)]

    def test_results_sorted_by_start(self) -> None:
        """Test that results are sorted by start position."""
        response = '''
        {
            "advertisements": [
                {"start": 500, "end": 600, "confidence": 0.9},
                {"start": 100, "end": 200, "confidence": 0.9},
                {"start": 300, "end": 400, "confidence": 0.9}
            ]
        }
        '''
        result = _parse_advertisement_response(response)

        assert result == [(100, 200), (300, 400), (500, 600)]


class TestParseTopicsResponse:
    """Tests for parsing topic extraction responses."""

    def test_parse_valid_response(self) -> None:
        """Test parsing a valid JSON array response."""
        response = '["Topic 1: Description", "Topic 2: Another description"]'
        result = _parse_topics_response(response)

        assert result == ["Topic 1: Description", "Topic 2: Another description"]

    def test_parse_response_with_surrounding_text(self) -> None:
        """Test parsing JSON array embedded in text."""
        response = '''
        Here are the topics:
        ["Topic 1", "Topic 2"]
        '''
        result = _parse_topics_response(response)

        assert result == ["Topic 1", "Topic 2"]

    def test_parse_empty_array(self) -> None:
        """Test parsing empty array."""
        response = "[]"
        result = _parse_topics_response(response)

        assert result == []

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON returns empty list."""
        response = "Not valid JSON"
        result = _parse_topics_response(response)

        assert result == []

    def test_filter_empty_items(self) -> None:
        """Test that empty items are filtered out."""
        response = '["Topic 1", "", "Topic 2", null]'
        result = _parse_topics_response(response)

        # Empty string and null should be filtered
        assert "Topic 1" in result
        assert "Topic 2" in result
        assert "" not in result


class TestParseKeywordsResponse:
    """Tests for parsing keyword extraction responses."""

    def test_parse_valid_response(self) -> None:
        """Test parsing a valid JSON array response."""
        response = '["keyword1", "keyword2", "keyword3"]'
        result = _parse_keywords_response(response)

        assert result == ["keyword1", "keyword2", "keyword3"]

    def test_parse_response_with_surrounding_text(self) -> None:
        """Test parsing JSON array embedded in text."""
        response = '''
        Keywords found:
        ["python", "podcast", "transcription"]
        '''
        result = _parse_keywords_response(response)

        assert result == ["python", "podcast", "transcription"]

    def test_parse_empty_array(self) -> None:
        """Test parsing empty array."""
        response = "[]"
        result = _parse_keywords_response(response)

        assert result == []

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON returns empty list."""
        response = "Not valid JSON"
        result = _parse_keywords_response(response)

        assert result == []


class TestDetectAdvertisements:
    """Tests for the detect_advertisements function.

    Validates: Requirements 6.1
    """

    def test_empty_text_returns_empty_list(self) -> None:
        """Test that empty text returns empty list without API call."""
        result = detect_advertisements(
            text="",
            api_key="test-key",
        )

        assert result == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        """Test that whitespace-only text returns empty list."""
        result = detect_advertisements(
            text="   \n\t  ",
            api_key="test-key",
        )

        assert result == []

    def test_missing_api_key_raises_error(self) -> None:
        """Test that missing API key raises ClaudeAPIUnavailableError."""
        with pytest.raises(ClaudeAPIUnavailableError) as exc_info:
            detect_advertisements(
                text="Some transcript text",
                api_key="",
            )

        assert "API key not configured" in str(exc_info.value)

    @patch("podtext.services.claude._create_client")
    def test_successful_detection(self, mock_create_client: MagicMock) -> None:
        """Test successful advertisement detection."""
        # Mock the client and response
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = '''
        {
            "advertisements": [
                {"start": 100, "end": 200, "confidence": 0.95}
            ]
        }
        '''
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        prompts = Prompts()
        result = detect_advertisements(
            text="Some transcript with ads",
            api_key="test-key",
            prompts=prompts,
        )

        assert result == [(100, 200)]
        mock_client.messages.create.assert_called_once()

    @patch("podtext.services.claude._create_client")
    def test_api_connection_error_raises_unavailable(
        self, mock_create_client: MagicMock
    ) -> None:
        """Test that connection errors raise ClaudeAPIUnavailableError.

        Validates: Requirements 6.4
        """
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.side_effect = APIConnectionError(
            request=MagicMock()
        )

        prompts = Prompts()
        with pytest.raises(ClaudeAPIUnavailableError):
            detect_advertisements(
                text="Some transcript",
                api_key="test-key",
                prompts=prompts,
            )

    @patch("podtext.services.claude._create_client")
    def test_authentication_error_raises_unavailable(
        self, mock_create_client: MagicMock
    ) -> None:
        """Test that authentication errors raise ClaudeAPIUnavailableError.

        Validates: Requirements 6.4
        """
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.side_effect = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(),
            body=None,
        )

        prompts = Prompts()
        with pytest.raises(ClaudeAPIUnavailableError):
            detect_advertisements(
                text="Some transcript",
                api_key="test-key",
                prompts=prompts,
            )


class TestDetectAdvertisementsSafe:
    """Tests for the detect_advertisements_safe function.

    Validates: Requirements 6.1, 6.4
    """

    def test_empty_text_returns_empty_list(self) -> None:
        """Test that empty text returns empty list."""
        result = detect_advertisements_safe(
            text="",
            api_key="test-key",
        )

        assert result == []

    def test_missing_api_key_returns_empty_with_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that missing API key returns empty list with warning.

        Validates: Requirements 6.4
        """
        result = detect_advertisements_safe(
            text="Some transcript",
            api_key="",
            warn_on_unavailable=True,
        )

        assert result == []
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "unavailable" in captured.err.lower()

    def test_missing_api_key_no_warning_when_disabled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that warning can be disabled."""
        prompts = Prompts()  # Provide prompts to avoid prompts file warning
        result = detect_advertisements_safe(
            text="Some transcript",
            api_key="",
            prompts=prompts,
            warn_on_unavailable=False,
        )

        assert result == []
        captured = capsys.readouterr()
        assert captured.err == ""

    @patch("podtext.services.claude._create_client")
    def test_api_error_returns_empty_with_warning(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that API errors return empty list with warning.

        Validates: Requirements 6.4
        """
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.side_effect = APIConnectionError(
            request=MagicMock()
        )

        prompts = Prompts()
        result = detect_advertisements_safe(
            text="Some transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=True,
        )

        assert result == []
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestAnalyzeContent:
    """Tests for the analyze_content function.

    Validates: Requirements 6.1, 6.4, 7.1
    """

    def test_empty_text_returns_empty_result(self) -> None:
        """Test that empty text returns empty AnalysisResult."""
        result = analyze_content(
            text="",
            api_key="test-key",
        )

        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []
        assert result.ad_markers == []

    def test_whitespace_only_returns_empty_result(self) -> None:
        """Test that whitespace-only text returns empty result."""
        result = analyze_content(
            text="   \n\t  ",
            api_key="test-key",
        )

        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []
        assert result.ad_markers == []

    def test_missing_api_key_returns_empty_with_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that missing API key returns empty result with warning.

        Validates: Requirements 6.4
        """
        result = analyze_content(
            text="Some transcript",
            api_key="",
            warn_on_unavailable=True,
        )

        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []
        assert result.ad_markers == []

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "unavailable" in captured.err.lower()

    def test_missing_api_key_no_warning_when_disabled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that warning can be disabled."""
        prompts = Prompts()  # Provide prompts to avoid prompts file warning
        result = analyze_content(
            text="Some transcript",
            api_key="",
            prompts=prompts,
            warn_on_unavailable=False,
        )

        assert result.summary == ""
        captured = capsys.readouterr()
        assert captured.err == ""

    @patch("podtext.services.claude._create_client")
    def test_successful_analysis(self, mock_create_client: MagicMock) -> None:
        """Test successful content analysis.

        Validates: Requirements 7.1
        """
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Set up responses for each API call
        responses = [
            # Summary response
            MagicMock(content=[MagicMock(text="This is a summary of the podcast.")]),
            # Topics response
            MagicMock(content=[MagicMock(text='["Topic 1: Description", "Topic 2: Another"]')]),
            # Keywords response
            MagicMock(content=[MagicMock(text='["keyword1", "keyword2"]')]),
            # Advertisement response
            MagicMock(content=[MagicMock(text='{"advertisements": [{"start": 100, "end": 200, "confidence": 0.9}]}')]),
        ]
        mock_client.messages.create.side_effect = responses

        prompts = Prompts()
        result = analyze_content(
            text="Some transcript text",
            api_key="test-key",
            prompts=prompts,
        )

        assert result.summary == "This is a summary of the podcast."
        assert result.topics == ["Topic 1: Description", "Topic 2: Another"]
        assert result.keywords == ["keyword1", "keyword2"]
        assert result.ad_markers == [(100, 200)]

        # Should have made 4 API calls
        assert mock_client.messages.create.call_count == 4

    @patch("podtext.services.claude._create_client")
    def test_api_unavailable_during_summary_returns_empty(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that API unavailability during summary returns empty result.

        Validates: Requirements 6.4
        """
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.side_effect = APIConnectionError(
            request=MagicMock()
        )

        prompts = Prompts()
        result = analyze_content(
            text="Some transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=True,
        )

        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []
        assert result.ad_markers == []

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch("podtext.services.claude._create_client")
    def test_partial_failure_continues(self, mock_create_client: MagicMock) -> None:
        """Test that partial API failures don't stop other analyses."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Summary succeeds, topics fails, keywords succeeds, ads fail
        def side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            call_count = mock_client.messages.create.call_count
            if call_count == 1:  # Summary
                return MagicMock(content=[MagicMock(text="Summary text")])
            elif call_count == 2:  # Topics - fail with APIError
                raise APIError(
                    message="Rate limited",
                    request=MagicMock(),
                    body=None,
                )
            elif call_count == 3:  # Keywords
                return MagicMock(content=[MagicMock(text='["keyword1"]')])
            else:  # Ads - fail
                raise APIError(
                    message="Rate limited",
                    request=MagicMock(),
                    body=None,
                )

        mock_client.messages.create.side_effect = side_effect

        prompts = Prompts()
        result = analyze_content(
            text="Some transcript",
            api_key="test-key",
            prompts=prompts,
        )

        # Summary and keywords should succeed
        assert result.summary == "Summary text"
        assert result.keywords == ["keyword1"]
        # Topics and ads should be empty due to failures
        assert result.topics == []
        assert result.ad_markers == []


class TestPromptsIntegration:
    """Tests for prompts integration with Claude client."""

    @patch("podtext.services.claude._create_client")
    @patch("podtext.services.claude.load_prompts")
    def test_loads_prompts_when_not_provided(
        self, mock_load_prompts: MagicMock, mock_create_client: MagicMock
    ) -> None:
        """Test that prompts are loaded when not provided."""
        mock_prompts = Prompts()
        mock_load_prompts.return_value = mock_prompts

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"advertisements": []}')]
        )

        detect_advertisements(
            text="Some text",
            api_key="test-key",
            prompts=None,  # Not provided
        )

        mock_load_prompts.assert_called_once_with(warn_on_fallback=True)

    @patch("podtext.services.claude._create_client")
    def test_uses_provided_prompts(self, mock_create_client: MagicMock) -> None:
        """Test that provided prompts are used."""
        custom_prompts = Prompts(
            advertisement_detection="Custom ad detection prompt"
        )

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"advertisements": []}')]
        )

        detect_advertisements(
            text="Some text",
            api_key="test-key",
            prompts=custom_prompts,
        )

        # Verify the custom prompt was used in the API call
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert "Custom ad detection prompt" in messages[0]["content"]
