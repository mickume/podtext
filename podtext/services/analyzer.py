"""Analyzer service for AI-powered transcript analysis."""

import re

from podtext.clients.claude import ClaudeClient
from podtext.config.manager import AnalysisPrompts, Config
from podtext.models.transcript import AdSegment, Analysis, Transcript


class AnalyzerError(Exception):
    """Exception raised for analyzer errors."""

    pass


class AnalyzerService:
    """Service for analyzing transcripts using Claude AI."""

    def __init__(self, config: Config, claude_client: ClaudeClient | None = None):
        """Initialize the analyzer service.

        Args:
            config: Application configuration
            claude_client: Claude API client (creates default if not provided)
        """
        self.config = config
        self.prompts = config.prompts
        self.claude = claude_client or ClaudeClient(config)

    def analyze(self, transcript: Transcript) -> Analysis:
        """Perform full analysis on a transcript.

        Args:
            transcript: Transcript to analyze

        Returns:
            Analysis object with summary, topics, keywords, and ad segments
        """
        text = transcript.get_text_with_paragraphs()

        # Generate all analysis components
        summary = self._generate_summary(text)
        topics = self._extract_topics(text)
        keywords = self._extract_keywords(text)
        ad_segments = self._detect_advertising(text)

        return Analysis(
            summary=summary,
            topics=topics,
            keywords=keywords,
            ad_segments=ad_segments,
        )

    def _generate_summary(self, text: str) -> str:
        """Generate a summary of the transcript."""
        if not self.prompts.summary:
            return ""

        try:
            return self.claude.analyze_summary(self.prompts.summary, text)
        except Exception as e:
            raise AnalyzerError(f"Failed to generate summary: {e}") from e

    def _extract_topics(self, text: str) -> list[str]:
        """Extract main topics from the transcript."""
        if not self.prompts.topics:
            return []

        try:
            return self.claude.analyze_topics(self.prompts.topics, text)
        except Exception as e:
            raise AnalyzerError(f"Failed to extract topics: {e}") from e

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from the transcript."""
        if not self.prompts.keywords:
            return []

        try:
            return self.claude.analyze_keywords(self.prompts.keywords, text)
        except Exception as e:
            raise AnalyzerError(f"Failed to extract keywords: {e}") from e

    def _detect_advertising(self, text: str) -> list[AdSegment]:
        """Detect advertising segments in the transcript."""
        if not self.prompts.advertising:
            return []

        try:
            response = self.claude.detect_advertising(self.prompts.advertising, text)
            return self._parse_ad_response(response, text)
        except Exception as e:
            # Non-fatal - continue without ad detection
            return []

    def _parse_ad_response(self, response: str, original_text: str) -> list[AdSegment]:
        """Parse the advertising detection response into AdSegment objects."""
        segments = []

        # Look for patterns in the response that indicate ad segments
        # Expected format from the prompt includes start/end quotes and advertiser

        lines = response.split("\n")
        current_segment: dict = {}

        for line in lines:
            line = line.strip()

            # Look for quoted text that marks start/end
            if "start" in line.lower():
                # Extract quoted text
                quotes = re.findall(r'"([^"]+)"', line)
                if quotes:
                    current_segment["start_text"] = quotes[0]

            elif "end" in line.lower():
                quotes = re.findall(r'"([^"]+)"', line)
                if quotes:
                    current_segment["end_text"] = quotes[0]

            elif "advertiser" in line.lower() or "product" in line.lower():
                # Extract the value after colon
                if ":" in line:
                    current_segment["advertiser"] = line.split(":", 1)[1].strip()

            elif "confidence" in line.lower():
                if "high" in line.lower():
                    current_segment["confidence"] = "high"
                elif "low" in line.lower():
                    current_segment["confidence"] = "low"
                else:
                    current_segment["confidence"] = "medium"

                # A confidence line typically marks the end of a segment description
                if "start_text" in current_segment:
                    segment = self._create_segment(current_segment, original_text)
                    if segment:
                        segments.append(segment)
                    current_segment = {}

        # Handle last segment if no confidence line
        if current_segment.get("start_text"):
            segment = self._create_segment(current_segment, original_text)
            if segment:
                segments.append(segment)

        return segments

    def _create_segment(self, data: dict, original_text: str) -> AdSegment | None:
        """Create an AdSegment from parsed data."""
        start_text = data.get("start_text", "")
        end_text = data.get("end_text", start_text)

        if not start_text:
            return None

        # Find positions in original text
        start_pos = original_text.lower().find(start_text.lower())
        end_pos = original_text.lower().rfind(end_text.lower())

        if end_pos >= 0:
            end_pos += len(end_text)

        return AdSegment(
            start_text=start_text,
            end_text=end_text,
            advertiser=data.get("advertiser", ""),
            confidence=data.get("confidence", "medium"),
            start_pos=start_pos,
            end_pos=end_pos,
        )

    def remove_advertising(self, text: str, ad_segments: list[AdSegment]) -> str:
        """Remove advertising segments from text.

        Only removes segments with high confidence detection.

        Args:
            text: Original transcript text
            ad_segments: List of detected ad segments

        Returns:
            Text with high-confidence ads replaced by marker
        """
        if not ad_segments:
            return text

        # Sort segments by position (reverse order for safe replacement)
        valid_segments = [
            seg
            for seg in ad_segments
            if seg.confidence == "high" and seg.start_pos >= 0 and seg.end_pos > seg.start_pos
        ]
        valid_segments.sort(key=lambda s: s.start_pos, reverse=True)

        result = text
        for seg in valid_segments:
            # Replace the segment with marker
            before = result[: seg.start_pos]
            after = result[seg.end_pos :]
            result = before + "[ADVERTISING REMOVED]" + after

        return result
