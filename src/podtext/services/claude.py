"""Claude API client for Podtext.

Handles advertisement detection and content analysis using Claude AI.
Integrates with the prompts loader for customizable prompts.

Requirements: 6.1, 6.4, 7.1
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field

import anthropic
from anthropic import (
    APIConnectionError,
    APIError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)

from podtext.core.prompts import Prompts, load_prompts

# Default Claude model to use
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30


class ClaudeAPIError(Exception):
    """Raised when Claude API encounters an error."""


class ClaudeAPIUnavailableError(ClaudeAPIError):
    """Raised when Claude API is unavailable.

    This indicates the API could not be reached or authentication failed,
    allowing callers to handle graceful degradation.

    Validates: Requirements 6.4
    """


class ClaudeRateLimitError(ClaudeAPIError):
    """Raised when Claude API rate limits are exceeded.

    This indicates the API has returned a rate limit error,
    and processing should be aborted.
    """


@dataclass
class AnalysisResult:
    """Result of content analysis from Claude API.

    Contains summary, topics, keywords, and advertisement markers
    extracted from the transcript.

    Validates: Requirements 7.1
    """

    summary: str = ""
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    ad_markers: list[tuple[int, int]] = field(default_factory=list)  # start, end positions


def _display_warning(message: str) -> None:
    """Display a warning message to stderr.

    Args:
        message: Warning message to display.
    """
    print(f"Warning: {message}", file=sys.stderr)


def _create_client(api_key: str) -> anthropic.Anthropic:
    """Create an Anthropic client instance.

    Args:
        api_key: The Anthropic API key.

    Returns:
        Configured Anthropic client.

    Raises:
        ClaudeAPIUnavailableError: If API key is empty.
    """
    if not api_key:
        raise ClaudeAPIUnavailableError(
            "Anthropic API key not configured. "
            "Set ANTHROPIC_API_KEY environment variable or configure in .podtext/config"
        )
    return anthropic.Anthropic(api_key=api_key)


def _call_claude(
    client: anthropic.Anthropic,
    prompt: str,
    text: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Make a call to Claude API with retry logic.

    Retries on transient errors (connection issues, server errors) with
    exponential backoff. Aborts immediately on rate limit errors.

    Args:
        client: Anthropic client instance.
        prompt: The system/instruction prompt.
        text: The text to analyze.
        model: Claude model to use.

    Returns:
        Claude's response text.

    Raises:
        ClaudeAPIUnavailableError: If API is unavailable after retries.
        ClaudeRateLimitError: If API rate limits are exceeded.
        ClaudeAPIError: If API returns an error.
    """
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n{text}",
                    }
                ],
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                content_block = message.content[0]
                if hasattr(content_block, "text"):
                    return content_block.text

            return ""

        except RateLimitError as e:
            # Rate limit errors should abort immediately
            _display_warning(
                f"Claude API rate limit exceeded: {e}. "
                "Please check your API usage limits and try again later."
            )
            raise ClaudeRateLimitError(f"Rate limit exceeded: {e}") from e

        except (APIConnectionError, AuthenticationError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                _display_warning(
                    f"Claude API connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {RETRY_DELAY_SECONDS} seconds..."
                )
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise ClaudeAPIUnavailableError(
                    f"Claude API unavailable after {MAX_RETRIES} attempts: {e}"
                ) from e

        except APIStatusError as e:
            # Server errors (5xx) should be retried
            if e.status_code >= 500:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    _display_warning(
                        f"Claude API server error (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {RETRY_DELAY_SECONDS} seconds..."
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    raise ClaudeAPIUnavailableError(
                        f"Claude API unavailable after {MAX_RETRIES} attempts: {e}"
                    ) from e
            else:
                # Client errors (4xx) should not be retried
                raise ClaudeAPIError(f"Claude API error: {e}") from e

        except APIError as e:
            raise ClaudeAPIError(f"Claude API error: {e}") from e

    # Should not reach here, but just in case
    if last_error:
        raise ClaudeAPIUnavailableError(
            f"Claude API unavailable after {MAX_RETRIES} attempts: {last_error}"
        ) from last_error
    raise ClaudeAPIError("Unknown error occurred")


def _parse_advertisement_response(response: str) -> list[tuple[int, int]]:
    """Parse advertisement detection response from Claude.

    Expects JSON format:
    {
        "advertisements": [
            {"start": <int>, "end": <int>, "confidence": <float>}
        ]
    }

    Only includes advertisements with confidence >= 0.8.

    Args:
        response: Claude's response text.

    Returns:
        List of (start, end) tuples for advertisement positions.
    """
    try:
        # Try to extract JSON from response
        # Claude might include explanation text around the JSON
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            return []

        json_str = response[json_start:json_end]
        data = json.loads(json_str)

        advertisements = data.get("advertisements", [])
        result: list[tuple[int, int]] = []

        for ad in advertisements:
            start = ad.get("start")
            end = ad.get("end")
            confidence = ad.get("confidence", 0.0)

            # Only include high-confidence advertisements
            if (
                isinstance(start, int)
                and isinstance(end, int)
                and isinstance(confidence, (int, float))
                and confidence >= 0.8
                and start >= 0
                and end > start
            ):
                result.append((start, end))

        # Sort by start position
        result.sort(key=lambda x: x[0])
        return result

    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _parse_topics_response(response: str) -> list[str]:
    """Parse topic extraction response from Claude.

    Expects JSON array format: ["Topic 1: description", ...]

    Args:
        response: Claude's response text.

    Returns:
        List of topic strings.
    """
    try:
        # Try to extract JSON array from response
        json_start = response.find("[")
        json_end = response.rfind("]") + 1

        if json_start == -1 or json_end == 0:
            return []

        json_str = response[json_start:json_end]
        data = json.loads(json_str)

        if isinstance(data, list):
            return [str(item) for item in data if item]
        return []

    except (json.JSONDecodeError, TypeError):
        return []


def _parse_keywords_response(response: str) -> list[str]:
    """Parse keyword extraction response from Claude.

    Expects JSON array format: ["keyword1", "keyword2", ...]

    Args:
        response: Claude's response text.

    Returns:
        List of keyword strings.
    """
    try:
        # Try to extract JSON array from response
        json_start = response.find("[")
        json_end = response.rfind("]") + 1

        if json_start == -1 or json_end == 0:
            return []

        json_str = response[json_start:json_end]
        data = json.loads(json_str)

        if isinstance(data, list):
            return [str(item) for item in data if item]
        return []

    except (json.JSONDecodeError, TypeError):
        return []


def detect_advertisements(
    text: str,
    api_key: str,
    prompts: Prompts | None = None,
    model: str = DEFAULT_MODEL,
) -> list[tuple[int, int]]:
    """Detect advertisement sections in transcript text.

    Sends the transcript to Claude API for advertisement detection.
    Returns positions of identified advertisement blocks.

    Args:
        text: The transcript text to analyze.
        api_key: Anthropic API key.
        prompts: Optional Prompts object. If None, loads from file.
        model: Claude model to use.

    Returns:
        List of (start, end) tuples indicating advertisement positions.

    Raises:
        ClaudeAPIUnavailableError: If API is unavailable.
        ClaudeAPIError: If API returns an error.

    Validates: Requirements 6.1
    """
    if not text.strip():
        return []

    # Load prompts if not provided
    if prompts is None:
        prompts = load_prompts(warn_on_fallback=True)

    client = _create_client(api_key)

    response = _call_claude(
        client=client,
        prompt=prompts.advertisement_detection,
        text=text,
        model=model,
    )

    return _parse_advertisement_response(response)


def analyze_content(
    text: str,
    api_key: str,
    prompts: Prompts | None = None,
    model: str = DEFAULT_MODEL,
    warn_on_unavailable: bool = True,
) -> AnalysisResult:
    """Analyze transcript content using Claude API.

    Performs comprehensive analysis including:
    - Content summary
    - Topic extraction
    - Keyword extraction
    - Advertisement detection

    Args:
        text: The transcript text to analyze.
        api_key: Anthropic API key.
        prompts: Optional Prompts object. If None, loads from file.
        model: Claude model to use.
        warn_on_unavailable: If True, display warning when API unavailable.

    Returns:
        AnalysisResult with summary, topics, keywords, and ad markers.
        Returns empty AnalysisResult if API is unavailable.

    Raises:
        ClaudeRateLimitError: If API rate limits are exceeded.

    Validates: Requirements 6.1, 6.4, 7.1
    """
    if not text.strip():
        return AnalysisResult()

    # Load prompts if not provided
    if prompts is None:
        prompts = load_prompts(warn_on_fallback=True)

    try:
        client = _create_client(api_key)
    except ClaudeAPIUnavailableError as e:
        if warn_on_unavailable:
            _display_warning(
                f"Claude API unavailable: {e}. Transcript will be output without AI analysis."
            )
        return AnalysisResult()

    result = AnalysisResult()

    # Get summary
    try:
        summary_response = _call_claude(
            client=client,
            prompt=prompts.content_summary,
            text=text,
            model=model,
        )
        result.summary = summary_response.strip()
    except ClaudeRateLimitError:
        # Rate limit errors should propagate up
        raise
    except ClaudeAPIUnavailableError as e:
        if warn_on_unavailable:
            _display_warning(
                f"Claude API unavailable during summary: {e}. "
                "Transcript will be output without AI analysis."
            )
        return AnalysisResult()
    except ClaudeAPIError:
        # Continue with other analyses even if one fails
        pass

    # Get topics
    try:
        topics_response = _call_claude(
            client=client,
            prompt=prompts.topic_extraction,
            text=text,
            model=model,
        )
        result.topics = _parse_topics_response(topics_response)
    except ClaudeRateLimitError:
        raise
    except ClaudeAPIError:
        pass

    # Get keywords
    try:
        keywords_response = _call_claude(
            client=client,
            prompt=prompts.keyword_extraction,
            text=text,
            model=model,
        )
        result.keywords = _parse_keywords_response(keywords_response)
    except ClaudeRateLimitError:
        raise
    except ClaudeAPIError:
        pass

    # Get advertisement markers
    try:
        ad_response = _call_claude(
            client=client,
            prompt=prompts.advertisement_detection,
            text=text,
            model=model,
        )
        result.ad_markers = _parse_advertisement_response(ad_response)
    except ClaudeRateLimitError:
        raise
    except ClaudeAPIError:
        pass

    return result


def detect_advertisements_safe(
    text: str,
    api_key: str,
    prompts: Prompts | None = None,
    model: str = DEFAULT_MODEL,
    warn_on_unavailable: bool = True,
) -> list[tuple[int, int]]:
    """Detect advertisements with graceful handling of API unavailability.

    Unlike detect_advertisements(), this function catches API unavailability
    errors and returns an empty list instead of raising an exception.
    Rate limit errors are still raised to abort processing.

    Args:
        text: The transcript text to analyze.
        api_key: Anthropic API key.
        prompts: Optional Prompts object. If None, loads from file.
        model: Claude model to use.
        warn_on_unavailable: If True, display warning when API unavailable.

    Returns:
        List of (start, end) tuples indicating advertisement positions.
        Returns empty list if API is unavailable.

    Raises:
        ClaudeRateLimitError: If API rate limits are exceeded.

    Validates: Requirements 6.1, 6.4
    """
    try:
        return detect_advertisements(
            text=text,
            api_key=api_key,
            prompts=prompts,
            model=model,
        )
    except ClaudeRateLimitError:
        # Rate limit errors should propagate
        raise
    except ClaudeAPIUnavailableError as e:
        if warn_on_unavailable:
            _display_warning(
                f"Claude API unavailable: {e}. "
                "Transcript will be output without advertisement removal."
            )
        return []
    except ClaudeAPIError as e:
        if warn_on_unavailable:
            _display_warning(
                f"Claude API error: {e}. Transcript will be output without advertisement removal."
            )
        return []
