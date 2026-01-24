"""Prompt management for Claude API integration."""

import re
import warnings
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Prompts:
    """Container for all LLM prompts."""

    advertisement_detection: str
    content_summary: str
    topic_extraction: str
    keyword_extraction: str


# Default prompts (used when file is missing or malformed)
# Note: Use double braces {{ }} to escape literal braces in format strings
DEFAULT_PROMPTS = Prompts(
    advertisement_detection="""Analyze the following podcast transcript and identify advertising sections.

For each advertisement section, provide:
1. The start position (character index) in the text
2. The end position (character index) in the text
3. Your confidence level (high, medium, low)

Only mark sections as advertisements if you are highly confident. These include:
- Explicit sponsor reads ("This episode is brought to you by...")
- Product promotions with promo codes
- Service endorsements with special offers

Return the results as JSON in this format:
{{"advertisements": [{{"start": 0, "end": 100, "confidence": "high"}}]}}

If no advertisements are found, return: {{"advertisements": []}}

Transcript:
{text}""",
    content_summary="""Summarize the following podcast transcript in 2-3 sentences.
Focus on the main topic and key takeaways.

Transcript:
{text}""",
    topic_extraction="""List the main topics covered in this podcast transcript.
For each topic, provide a single sentence description.
Return as a JSON array of strings.

Format: ["Topic 1: Brief description", "Topic 2: Brief description"]

Transcript:
{text}""",
    keyword_extraction="""Extract relevant keywords from this podcast transcript.
Include names, concepts, technologies, and important terms.
Return as a JSON array of strings, maximum 20 keywords.

Format: ["keyword1", "keyword2", "keyword3"]

Transcript:
{text}""",
)


def get_prompts_file_path() -> Path:
    """Get the default path for the prompts file."""
    return Path.cwd() / ".podtext" / "prompts.md"


def _parse_prompts_markdown(content: str) -> Prompts | None:
    """
    Parse prompts from markdown content.

    Expected format:
    # Advertisement Detection
    <prompt text>

    # Content Summary
    <prompt text>

    etc.
    """
    # Pattern to match sections: # Section Name followed by content
    section_pattern = re.compile(
        r"^#\s+(.+?)\s*$\n(.*?)(?=^#\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    sections = {}
    for match in section_pattern.finditer(content):
        title = match.group(1).strip().lower()
        body = match.group(2).strip()
        sections[title] = body

    # Map section titles to prompt fields
    title_mapping = {
        "advertisement detection": "advertisement_detection",
        "content summary": "content_summary",
        "topic extraction": "topic_extraction",
        "keyword extraction": "keyword_extraction",
    }

    prompts_dict = {}
    for title, field in title_mapping.items():
        if title in sections and sections[title]:
            prompts_dict[field] = sections[title]

    # All four prompts must be present
    required_fields = {"advertisement_detection", "content_summary", "topic_extraction", "keyword_extraction"}
    if not required_fields.issubset(prompts_dict.keys()):
        return None

    return Prompts(**prompts_dict)


def load_prompts(prompts_path: Path | None = None) -> Prompts:
    """
    Load prompts from markdown file.

    Falls back to default prompts if file is missing or malformed.

    Args:
        prompts_path: Optional path to prompts file

    Returns:
        Prompts object with all prompt templates
    """
    if prompts_path is None:
        prompts_path = get_prompts_file_path()

    if not prompts_path.exists():
        warnings.warn(
            f"Prompts file not found at {prompts_path}. Using default prompts.",
            UserWarning,
            stacklevel=2,
        )
        return DEFAULT_PROMPTS

    try:
        content = prompts_path.read_text(encoding="utf-8")
        parsed = _parse_prompts_markdown(content)

        if parsed is None:
            warnings.warn(
                f"Prompts file at {prompts_path} is malformed. Using default prompts.",
                UserWarning,
                stacklevel=2,
            )
            return DEFAULT_PROMPTS

        return parsed

    except OSError as e:
        warnings.warn(
            f"Failed to read prompts file: {e}. Using default prompts.",
            UserWarning,
            stacklevel=2,
        )
        return DEFAULT_PROMPTS


def create_default_prompts_file(prompts_path: Path | None = None) -> Path:
    """
    Create a prompts file with default content.

    Args:
        prompts_path: Optional path for the prompts file

    Returns:
        Path to the created file
    """
    if prompts_path is None:
        prompts_path = get_prompts_file_path()

    prompts_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# Advertisement Detection

{DEFAULT_PROMPTS.advertisement_detection}

# Content Summary

{DEFAULT_PROMPTS.content_summary}

# Topic Extraction

{DEFAULT_PROMPTS.topic_extraction}

# Keyword Extraction

{DEFAULT_PROMPTS.keyword_extraction}
"""

    prompts_path.write_text(content, encoding="utf-8")
    return prompts_path
