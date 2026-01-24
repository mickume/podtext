"""Claude API client for content analysis."""

import json
import warnings
from dataclasses import dataclass

import anthropic

from podtext.models import AnalysisResult
from podtext.prompts import Prompts, load_prompts


class ClaudeAPIError(Exception):
    """Exception raised when Claude API request fails."""

    pass


@dataclass
class ClaudeClient:
    """Client for interacting with Claude API."""

    api_key: str
    model: str = "claude-sonnet-4-20250514"
    _client: anthropic.Anthropic | None = None
    _prompts: Prompts | None = None

    def __post_init__(self) -> None:
        """Initialize the Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        if self._prompts is None:
            self._prompts = load_prompts()

    @property
    def prompts(self) -> Prompts:
        """Get the loaded prompts."""
        if self._prompts is None:
            self._prompts = load_prompts()
        return self._prompts

    def reload_prompts(self) -> None:
        """Reload prompts from file (for runtime updates)."""
        self._prompts = load_prompts()

    def _call_api(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Call Claude API with the given prompt.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response

        Returns:
            The response text

        Raises:
            ClaudeAPIError: If the API call fails
        """
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            raise ClaudeAPIError(f"Claude API error: {e}") from e
        except Exception as e:
            raise ClaudeAPIError(f"Unexpected error calling Claude API: {e}") from e

    def detect_advertisements(self, text: str) -> list[tuple[int, int]]:
        """
        Detect advertisement sections in transcript text.

        Args:
            text: The transcript text to analyze

        Returns:
            List of (start, end) position tuples for each advertisement
        """
        prompt = self.prompts.advertisement_detection.format(text=text)

        try:
            response = self._call_api(prompt)
            # Parse JSON response
            data = json.loads(response)
            ads = data.get("advertisements", [])

            # Filter to high confidence only and extract positions
            return [
                (ad["start"], ad["end"])
                for ad in ads
                if ad.get("confidence") == "high"
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            warnings.warn(
                f"Failed to parse advertisement detection response: {e}",
                UserWarning,
                stacklevel=2,
            )
            return []
        except ClaudeAPIError:
            # Re-raise API errors
            raise

    def summarize_content(self, text: str) -> str:
        """
        Generate a summary of the transcript.

        Args:
            text: The transcript text to summarize

        Returns:
            Summary string
        """
        prompt = self.prompts.content_summary.format(text=text)
        return self._call_api(prompt)

    def extract_topics(self, text: str) -> list[str]:
        """
        Extract main topics from the transcript.

        Args:
            text: The transcript text to analyze

        Returns:
            List of topic descriptions
        """
        prompt = self.prompts.topic_extraction.format(text=text)

        try:
            response = self._call_api(prompt)
            # Try to parse as JSON array
            topics = json.loads(response)
            if isinstance(topics, list):
                return [str(t) for t in topics]
            return []
        except json.JSONDecodeError:
            # Try to extract topics from plain text
            lines = response.strip().split("\n")
            return [line.strip("- ").strip() for line in lines if line.strip()]

    def extract_keywords(self, text: str) -> list[str]:
        """
        Extract keywords from the transcript.

        Args:
            text: The transcript text to analyze

        Returns:
            List of keywords
        """
        prompt = self.prompts.keyword_extraction.format(text=text)

        try:
            response = self._call_api(prompt)
            keywords = json.loads(response)
            if isinstance(keywords, list):
                return [str(k) for k in keywords[:20]]  # Max 20 keywords
            return []
        except json.JSONDecodeError:
            # Try to extract from plain text
            words = response.strip().replace(",", " ").split()
            return [w.strip() for w in words if w.strip()][:20]

    def analyze_content(self, text: str) -> AnalysisResult:
        """
        Perform full content analysis on transcript.

        Args:
            text: The transcript text to analyze

        Returns:
            AnalysisResult with summary, topics, keywords, and ad markers
        """
        # Detect advertisements first
        ad_markers = self.detect_advertisements(text)

        # Get summary
        summary = self.summarize_content(text)

        # Extract topics
        topics = self.extract_topics(text)

        # Extract keywords
        keywords = self.extract_keywords(text)

        return AnalysisResult(
            summary=summary,
            topics=topics,
            keywords=keywords,
            ad_markers=ad_markers,
        )


def create_claude_client(api_key: str | None) -> ClaudeClient | None:
    """
    Create a Claude client if API key is available.

    Args:
        api_key: The Anthropic API key

    Returns:
        ClaudeClient or None if no API key provided
    """
    if not api_key:
        return None
    return ClaudeClient(api_key=api_key)


def analyze_with_fallback(
    text: str,
    api_key: str | None,
) -> AnalysisResult | None:
    """
    Analyze content with Claude, with graceful fallback.

    Args:
        text: The transcript text
        api_key: The Anthropic API key

    Returns:
        AnalysisResult or None if Claude is unavailable
    """
    if not api_key:
        warnings.warn(
            "Claude API key not configured. Skipping AI analysis.",
            UserWarning,
            stacklevel=2,
        )
        return None

    client = create_claude_client(api_key)
    if client is None:
        return None

    try:
        return client.analyze_content(text)
    except ClaudeAPIError as e:
        warnings.warn(
            f"Claude API unavailable: {e}. Outputting transcript without AI analysis.",
            UserWarning,
            stacklevel=2,
        )
        return None
