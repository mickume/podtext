"""Prompt management for Podtext.

Handles loading Claude API prompts from an editable markdown file,
with built-in defaults as fallback.

Requirements: 9.1, 9.2, 9.3
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Default prompts file paths (same pattern as config)
LOCAL_PROMPTS_PATH = Path(".podtext/prompts.md")
GLOBAL_PROMPTS_PATH = Path.home() / ".podtext" / "prompts.md"

# Built-in default prompts
DEFAULT_ADVERTISEMENT_DETECTION_PROMPT = """Analyze the following transcript and identify \
advertising sections.

For each advertisement section found, provide:
1. The start position (character index) in the text
2. The end position (character index) in the text
3. A confidence score (0.0 to 1.0)

Only include sections with high confidence (>= 0.8) as advertisements.

Respond in JSON format:
{
  "advertisements": [
    {"start": <int>, "end": <int>, "confidence": <float>}
  ]
}

Transcript:
"""

DEFAULT_CONTENT_SUMMARY_PROMPT = """Summarize the following podcast transcript in 2-3 paragraphs.
Focus on the main points discussed and key takeaways.

Transcript:
"""

DEFAULT_TOPIC_EXTRACTION_PROMPT = """List the main topics covered in the following \
podcast transcript.
For each topic, provide a one-sentence description.

Format your response as a JSON array of strings:
["Topic 1: description", "Topic 2: description", ...]

Transcript:
"""

DEFAULT_KEYWORD_EXTRACTION_PROMPT = """Extract the most important keywords from the \
following podcast transcript.
Focus on key names, core concepts, technologies, and broader categories.
Limit to 20 keywords maximum, prioritizing the most significant terms.

Format your response as a JSON array of strings:
["keyword1", "keyword2", ...]

Transcript:
"""


class PromptsError(Exception):
    """Raised when prompts cannot be loaded or parsed."""


@dataclass
class Prompts:
    """Container for all Claude API prompts.

    Holds the prompt templates used for various Claude API calls
    including advertisement detection, content summarization,
    topic extraction, and keyword extraction.
    """

    advertisement_detection: str = DEFAULT_ADVERTISEMENT_DETECTION_PROMPT
    content_summary: str = DEFAULT_CONTENT_SUMMARY_PROMPT
    topic_extraction: str = DEFAULT_TOPIC_EXTRACTION_PROMPT
    keyword_extraction: str = DEFAULT_KEYWORD_EXTRACTION_PROMPT

    @classmethod
    def defaults(cls) -> Prompts:
        """Create a Prompts instance with all default values.

        Returns:
            Prompts instance with built-in default prompts.
        """
        return cls()


def _parse_prompts_markdown(content: str) -> dict[str, str]:
    """Parse prompts from markdown content.

    The markdown file should have sections with H1 headers:
    - # Advertisement Detection
    - # Content Summary
    - # Topic Extraction
    - # Keyword Extraction

    Args:
        content: Markdown file content.

    Returns:
        Dictionary mapping section names to prompt content.

    Raises:
        PromptsError: If the markdown structure is invalid.
    """
    # Split content by H1 headers
    # Pattern matches "# Header Name" at the start of a line
    sections = re.split(r"^#\s+", content, flags=re.MULTILINE)

    prompts: dict[str, str] = {}

    for section in sections:
        if not section.strip():
            continue

        # First line is the header, rest is content
        lines = section.split("\n", 1)
        if len(lines) < 2:
            continue

        header = lines[0].strip().lower()
        prompt_content = lines[1].strip()

        if not prompt_content:
            continue

        # Map header names to prompt keys
        if "advertisement" in header and "detection" in header:
            prompts["advertisement_detection"] = prompt_content
        elif "content" in header and "summary" in header:
            prompts["content_summary"] = prompt_content
        elif "topic" in header and "extraction" in header:
            prompts["topic_extraction"] = prompt_content
        elif "keyword" in header and "extraction" in header:
            prompts["keyword_extraction"] = prompt_content

    return prompts


def _display_warning(message: str) -> None:
    """Display a warning message to stderr.

    Args:
        message: Warning message to display.
    """
    print(f"Warning: {message}", file=sys.stderr)


def load_prompts(
    local_path: Path | None = None,
    global_path: Path | None = None,
    warn_on_fallback: bool = True,
) -> Prompts:
    """Load prompts from markdown file at runtime.

    Attempts to load prompts from the local path first, then global path.
    Falls back to built-in defaults if file is missing or malformed.

    Args:
        local_path: Override path for local prompts file.
        global_path: Override path for global prompts file.
        warn_on_fallback: If True, display warning when using defaults.

    Returns:
        Prompts object with loaded or default prompts.

    Validates: Requirements 9.1, 9.2, 9.3
    """
    local_path = local_path or LOCAL_PROMPTS_PATH
    global_path = global_path or GLOBAL_PROMPTS_PATH

    # Try local path first
    prompts_path: Path | None = None
    if local_path.exists():
        prompts_path = local_path
    elif global_path.exists():
        prompts_path = global_path

    # If no prompts file found, create default file and use defaults
    if prompts_path is None:
        try:
            # Create in local .podtext if it exists, otherwise use global
            if local_path.parent.exists():
                target_path = local_path
            else:
                target_path = global_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(generate_default_prompts_markdown(), encoding="utf-8")
        except OSError:
            pass  # Silently ignore if we can't create the file
        return Prompts.defaults()

    # Try to load and parse the prompts file
    try:
        content = prompts_path.read_text(encoding="utf-8")
        parsed_prompts = _parse_prompts_markdown(content)

        # Check if we got any valid prompts
        if not parsed_prompts:
            if warn_on_fallback:
                _display_warning(
                    f"Prompts file {prompts_path} is malformed (no valid sections found). "
                    "Using built-in default prompts."
                )
            return Prompts.defaults()

        # Create Prompts object, using defaults for any missing sections
        return Prompts(
            advertisement_detection=parsed_prompts.get(
                "advertisement_detection", DEFAULT_ADVERTISEMENT_DETECTION_PROMPT
            ),
            content_summary=parsed_prompts.get("content_summary", DEFAULT_CONTENT_SUMMARY_PROMPT),
            topic_extraction=parsed_prompts.get(
                "topic_extraction", DEFAULT_TOPIC_EXTRACTION_PROMPT
            ),
            keyword_extraction=parsed_prompts.get(
                "keyword_extraction", DEFAULT_KEYWORD_EXTRACTION_PROMPT
            ),
        )

    except OSError as e:
        if warn_on_fallback:
            _display_warning(
                f"Could not read prompts file {prompts_path}: {e}. Using built-in default prompts."
            )
        return Prompts.defaults()
    except Exception as e:
        if warn_on_fallback:
            _display_warning(
                f"Error parsing prompts file {prompts_path}: {e}. Using built-in default prompts."
            )
        return Prompts.defaults()


def get_prompts() -> Prompts:
    """Get prompts using default paths.

    Convenience function that loads prompts from standard paths.

    Returns:
        Prompts object with loaded or default prompts.
    """
    return load_prompts()


def generate_default_prompts_markdown() -> str:
    """Generate the default prompts as a markdown file content.

    This can be used to create an initial prompts file for customization.

    Returns:
        Markdown-formatted string with all default prompts.
    """
    return f"""# Advertisement Detection

{DEFAULT_ADVERTISEMENT_DETECTION_PROMPT}

# Content Summary

{DEFAULT_CONTENT_SUMMARY_PROMPT}

# Topic Extraction

{DEFAULT_TOPIC_EXTRACTION_PROMPT}

# Keyword Extraction

{DEFAULT_KEYWORD_EXTRACTION_PROMPT}
"""
