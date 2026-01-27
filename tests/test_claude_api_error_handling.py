"""Tests for Claude API error handling improvements.

This test suite verifies that API errors (like insufficient credits, invalid
requests, etc.) are properly reported to users instead of being silently ignored.
"""

from unittest.mock import MagicMock, patch

import pytest
from anthropic import APIError

from podtext.services.claude import AnalysisResult, ClaudeAPIError, analyze_content
from podtext.core.prompts import Prompts


class TestAPIErrorReporting:
    """Tests for proper error reporting when API calls fail."""

    @patch("podtext.services.claude._create_client")
    def test_api_error_during_summary_displays_warning(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that API errors during summary are reported to user.

        This addresses the bug where 400 errors (like insufficient credits)
        were silently ignored, leaving users confused about missing analysis.
        """
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Simulate API error (e.g., insufficient credits)
        mock_client.messages.create.side_effect = APIError(
            message="Your credit balance is too low",
            request=MagicMock(),
            body=None,
        )

        prompts = Prompts()
        result = analyze_content(
            text="Test transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=True,
        )

        # Should return empty result
        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []
        assert result.ad_markers == []

        # Should display warning about the error
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Claude API error during summary" in captured.err
        assert "Transcript will be output without AI analysis" in captured.err

    @patch("podtext.services.claude._create_client")
    def test_api_error_no_warning_when_disabled(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that warnings can be suppressed with warn_on_unavailable=False."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        mock_client.messages.create.side_effect = APIError(
            message="API error",
            request=MagicMock(),
            body=None,
        )

        prompts = Prompts()
        result = analyze_content(
            text="Test transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=False,  # Warnings disabled
        )

        # Should return empty result
        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []

        # Should NOT display warning
        captured = capsys.readouterr()
        assert "Warning" not in captured.err

    @patch("podtext.services.claude._create_client")
    def test_api_error_during_topics_displays_warning(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that API errors during topic extraction are reported."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Summary succeeds, topics fails
        def side_effect(*args, **kwargs):
            call_count = mock_client.messages.create.call_count
            if call_count == 1:  # Summary
                return MagicMock(content=[MagicMock(text="Summary text")])
            else:  # Topics - fail
                raise APIError(
                    message="API error",
                    request=MagicMock(),
                    body=None,
                )

        mock_client.messages.create.side_effect = side_effect

        prompts = Prompts()
        result = analyze_content(
            text="Test transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=True,
        )

        # Summary should succeed, topics should be empty
        assert result.summary == "Summary text"
        assert result.topics == []

        # Should display warning about topics error
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Claude API error during topic extraction" in captured.err

    @patch("podtext.services.claude._create_client")
    def test_api_error_during_keywords_displays_warning(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that API errors during keyword extraction are reported."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Summary and topics succeed, keywords fails
        def side_effect(*args, **kwargs):
            call_count = mock_client.messages.create.call_count
            if call_count == 1:  # Summary
                return MagicMock(content=[MagicMock(text="Summary")])
            elif call_count == 2:  # Topics
                return MagicMock(content=[MagicMock(text='["Topic 1"]')])
            else:  # Keywords - fail
                raise APIError(
                    message="API error",
                    request=MagicMock(),
                    body=None,
                )

        mock_client.messages.create.side_effect = side_effect

        prompts = Prompts()
        result = analyze_content(
            text="Test transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=True,
        )

        # Summary and topics should succeed, keywords should be empty
        assert result.summary == "Summary"
        assert result.topics == ["Topic 1"]
        assert result.keywords == []

        # Should display warning about keywords error
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Claude API error during keyword extraction" in captured.err

    @patch("podtext.services.claude._create_client")
    def test_api_error_during_ads_displays_warning(
        self, mock_create_client: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that API errors during ad detection are reported."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # First 3 succeed, ads fails
        def side_effect(*args, **kwargs):
            call_count = mock_client.messages.create.call_count
            if call_count <= 3:
                return MagicMock(content=[MagicMock(text="Success")])
            else:  # Ads - fail
                raise APIError(
                    message="API error",
                    request=MagicMock(),
                    body=None,
                )

        mock_client.messages.create.side_effect = side_effect

        prompts = Prompts()
        result = analyze_content(
            text="Test transcript",
            api_key="test-key",
            prompts=prompts,
            warn_on_unavailable=True,
        )

        # First 3 should succeed, ads should be empty
        assert result.summary == "Success"
        assert result.ad_markers == []

        # Should display warning about ads error
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Claude API error during advertisement detection" in captured.err
