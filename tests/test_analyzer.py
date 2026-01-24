"""Tests for analyzer service."""

from unittest.mock import MagicMock, patch

import pytest

from podtext.config.manager import AnalysisPrompts, Config
from podtext.models.transcript import AdSegment, Analysis, Transcript
from podtext.services.analyzer import AnalyzerService


class TestAnalyzerService:
    """Tests for AnalyzerService."""

    def test_analyze_calls_all_methods(self):
        """Test that analyze calls all analysis methods."""
        config = Config()
        config.prompts = AnalysisPrompts(
            summary="Summarize",
            topics="List topics",
            keywords="Extract keywords",
            advertising="Find ads",
        )

        mock_claude = MagicMock()
        mock_claude.analyze_summary.return_value = "Summary text"
        mock_claude.analyze_topics.return_value = ["Topic 1", "Topic 2"]
        mock_claude.analyze_keywords.return_value = ["key1", "key2"]
        mock_claude.detect_advertising.return_value = ""

        service = AnalyzerService(config, claude_client=mock_claude)

        transcript = Transcript(text="Test transcript content.")
        result = service.analyze(transcript)

        assert isinstance(result, Analysis)
        assert result.summary == "Summary text"
        assert result.topics == ["Topic 1", "Topic 2"]
        assert result.keywords == ["key1", "key2"]

    def test_analyze_skips_empty_prompts(self):
        """Test that empty prompts are skipped."""
        config = Config()
        config.prompts = AnalysisPrompts()  # All empty

        mock_claude = MagicMock()
        service = AnalyzerService(config, claude_client=mock_claude)

        transcript = Transcript(text="Test content.")
        result = service.analyze(transcript)

        # Should not call claude methods with empty prompts
        mock_claude.analyze_summary.assert_not_called()
        mock_claude.analyze_topics.assert_not_called()
        mock_claude.analyze_keywords.assert_not_called()

        assert result.summary == ""
        assert result.topics == []
        assert result.keywords == []

    def test_remove_advertising_high_confidence(self):
        """Test advertising removal with high confidence."""
        config = Config()
        service = AnalyzerService.__new__(AnalyzerService)

        text = "Start of episode. This is sponsored by Acme. Buy now! Back to content. End."
        ad_segments = [
            AdSegment(
                start_text="This is sponsored",
                end_text="Buy now!",
                confidence="high",
                start_pos=18,
                end_pos=50,
            )
        ]

        result = service.remove_advertising(text, ad_segments)

        assert "[ADVERTISING REMOVED]" in result
        assert "sponsored" not in result
        assert "Start of episode" in result
        assert "Back to content" in result

    def test_remove_advertising_ignores_low_confidence(self):
        """Test that low confidence ads are not removed."""
        config = Config()
        service = AnalyzerService.__new__(AnalyzerService)

        text = "Content with maybe ad mention here."
        ad_segments = [
            AdSegment(
                start_text="maybe ad",
                end_text="here",
                confidence="low",
                start_pos=13,
                end_pos=35,
            )
        ]

        result = service.remove_advertising(text, ad_segments)

        assert "[ADVERTISING REMOVED]" not in result
        assert "maybe ad" in result

    def test_remove_advertising_multiple_segments(self):
        """Test removing multiple ad segments."""
        config = Config()
        service = AnalyzerService.__new__(AnalyzerService)

        text = "Intro. Ad one here. Content. Ad two here. Outro."
        ad_segments = [
            AdSegment(
                start_text="Ad one",
                end_text="here",
                confidence="high",
                start_pos=7,
                end_pos=19,
            ),
            AdSegment(
                start_text="Ad two",
                end_text="here",
                confidence="high",
                start_pos=29,
                end_pos=41,
            ),
        ]

        result = service.remove_advertising(text, ad_segments)

        assert result.count("[ADVERTISING REMOVED]") == 2
        assert "Intro" in result
        assert "Content" in result
        assert "Outro" in result


class TestAdResponseParsing:
    """Tests for advertising response parsing."""

    def test_parse_ad_response_with_quotes(self):
        """Test parsing ad response with quoted text."""
        config = Config()
        config.prompts = AnalysisPrompts()
        mock_claude = MagicMock()
        service = AnalyzerService(config, claude_client=mock_claude)

        response = '''
1. Advertising segment:
   - Start: "This episode is brought to you by"
   - End: "now back to the show"
   - Advertiser: Acme Corp
   - Confidence: high
'''
        original_text = (
            "Hello. This episode is brought to you by Acme. "
            "Great products! Now back to the show. Goodbye."
        ).lower()

        segments = service._parse_ad_response(response, original_text)

        assert len(segments) == 1
        assert segments[0].start_text == "This episode is brought to you by"
        assert segments[0].end_text == "now back to the show"
        assert segments[0].advertiser == "Acme Corp"
        assert segments[0].confidence == "high"

    def test_parse_ad_response_empty(self):
        """Test parsing empty response."""
        config = Config()
        config.prompts = AnalysisPrompts()
        mock_claude = MagicMock()
        service = AnalyzerService(config, claude_client=mock_claude)

        response = "No advertising was detected in this transcript."

        segments = service._parse_ad_response(response, "original text")

        assert len(segments) == 0
