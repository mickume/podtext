"""Claude API client for content analysis.

Handles advertisement detection and content analysis using Claude.
"""

import json
import warnings
from typing import Optional

import anthropic

from .models import AnalysisResult
from .prompts import load_prompts, get_prompt


class ClaudeAPIError(Exception):
    """Error from Claude API."""

    pass


# Global prompt cache for runtime loading
_prompts_cache: Optional[dict[str, str]] = None


def _get_prompts() -> dict[str, str]:
    """Get prompts, reloading from file each time for runtime updates."""
    global _prompts_cache
    # Always reload to support runtime modifications (Property 13)
    _prompts_cache = load_prompts()
    return _prompts_cache


def _clear_prompts_cache():
    """Clear the prompts cache (for testing)."""
    global _prompts_cache
    _prompts_cache = None


def _create_client(api_key: str) -> anthropic.Anthropic:
    """Create an Anthropic client."""
    return anthropic.Anthropic(api_key=api_key)


def detect_advertisements(
    text: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> list[tuple[int, int]]:
    """Detect advertisements in transcript text.

    Args:
        text: Transcript text to analyze.
        api_key: Anthropic API key.
        model: Claude model to use.

    Returns:
        List of (start, end) tuples marking advertisement positions.
        Returns empty list if API is unavailable.
    """
    if not api_key:
        warnings.warn(
            "No API key provided, skipping advertisement detection.",
            UserWarning,
        )
        return []

    prompts = _get_prompts()
    prompt = get_prompt("advertisement_detection", prompts, text=text)

    try:
        client = _create_client(api_key)
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        # Parse JSON response
        # Try to extract JSON from the response
        try:
            # Look for JSON array in response
            json_match = response_text
            if "[" in response_text:
                start = response_text.index("[")
                end = response_text.rindex("]") + 1
                json_match = response_text[start:end]

            ads = json.loads(json_match)
            return [(ad["start"], ad["end"]) for ad in ads if ad.get("confidence") == "high"]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    except anthropic.APIError as e:
        warnings.warn(
            f"Claude API error during advertisement detection: {e}. Continuing without ad removal.",
            UserWarning,
        )
        return []
    except Exception as e:
        warnings.warn(
            f"Unexpected error during advertisement detection: {e}. Continuing without ad removal.",
            UserWarning,
        )
        return []


def analyze_content(
    text: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> AnalysisResult:
    """Analyze transcript content for summary, topics, and keywords.

    Args:
        text: Transcript text to analyze.
        api_key: Anthropic API key.
        model: Claude model to use.

    Returns:
        AnalysisResult with summary, topics, keywords.
        Returns empty result if API is unavailable.
    """
    if not api_key:
        warnings.warn(
            "No API key provided, skipping content analysis.",
            UserWarning,
        )
        return AnalysisResult(summary="", topics=[], keywords=[])

    prompts = _get_prompts()

    try:
        client = _create_client(api_key)

        # Get summary
        summary_prompt = get_prompt("content_summary", prompts, text=text)
        summary_response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": summary_prompt}],
        )
        summary = summary_response.content[0].text.strip()

        # Get topics
        topics_prompt = get_prompt("topic_extraction", prompts, text=text)
        topics_response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": topics_prompt}],
        )
        topics_text = topics_response.content[0].text
        topics = _parse_json_array(topics_text)

        # Get keywords
        keywords_prompt = get_prompt("keyword_extraction", prompts, text=text)
        keywords_response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": keywords_prompt}],
        )
        keywords_text = keywords_response.content[0].text
        keywords = _parse_json_array(keywords_text)

        return AnalysisResult(
            summary=summary,
            topics=topics,
            keywords=keywords,
        )

    except anthropic.APIError as e:
        warnings.warn(
            f"Claude API error during content analysis: {e}. Returning empty analysis.",
            UserWarning,
        )
        return AnalysisResult(summary="", topics=[], keywords=[])
    except Exception as e:
        warnings.warn(
            f"Unexpected error during content analysis: {e}. Returning empty analysis.",
            UserWarning,
        )
        return AnalysisResult(summary="", topics=[], keywords=[])


def _parse_json_array(text: str) -> list[str]:
    """Parse a JSON array from text, handling common formatting issues."""
    try:
        # Try to extract JSON array from response
        if "[" in text:
            start = text.index("[")
            end = text.rindex("]") + 1
            json_text = text[start:end]
            result = json.loads(json_text)
            if isinstance(result, list):
                return [str(item) for item in result]
        return []
    except (json.JSONDecodeError, ValueError):
        return []
