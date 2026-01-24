"""Prompt management for Claude API.

Loads prompts from markdown file at runtime with fallback to defaults.
"""

import re
from pathlib import Path
from typing import Optional
import warnings


# Default prompts used when file is missing or malformed
DEFAULT_PROMPTS = {
    "advertisement_detection": """\
Analyze the following podcast transcript and identify any advertising or sponsored content sections.

For each advertisement, provide:
1. The start and end character positions in the transcript
2. A confidence score (high, medium, low)

Only mark sections as advertisements if you are confident they are promotional content,
not just mentions of products or services in the context of the discussion.

Return your response as a JSON array of objects with keys: start, end, confidence.
If no advertisements are found, return an empty array: []

Transcript:
{text}
""",

    "content_summary": """\
Summarize the following podcast transcript in 2-3 sentences.
Focus on the main topics discussed and key takeaways.

Transcript:
{text}
""",

    "topic_extraction": """\
List the main topics covered in this podcast transcript.
Provide each topic as a single sentence description.
Return as a JSON array of strings.

Transcript:
{text}
""",

    "keyword_extraction": """\
Extract relevant keywords from this podcast transcript.
Include names, concepts, technologies, and key terms discussed.
Return as a JSON array of strings (10-20 keywords).

Transcript:
{text}
""",
}


def _parse_prompts_markdown(content: str) -> dict[str, str]:
    """Parse prompts from markdown content.

    Expected format:
    # Section Title

    Prompt content here...

    # Another Section

    Another prompt...
    """
    prompts = {}

    # Split by headers
    sections = re.split(r'^#\s+(.+)$', content, flags=re.MULTILINE)

    # sections[0] is content before first header (usually empty)
    # sections[1::2] are header titles
    # sections[2::2] are content after each header

    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            title = sections[i].strip()
            content_text = sections[i + 1].strip()

            # Convert title to key format (lowercase, underscores)
            key = title.lower().replace(" ", "_").replace("-", "_")

            prompts[key] = content_text

    return prompts


def load_prompts(prompts_path: Optional[Path] = None) -> dict[str, str]:
    """Load prompts from markdown file.

    Args:
        prompts_path: Path to prompts markdown file. If None, uses default location.

    Returns:
        Dictionary mapping prompt names to prompt text.
        Falls back to defaults if file is missing or malformed.
    """
    if prompts_path is None:
        prompts_path = Path(".podtext") / "prompts.md"

    if not prompts_path.exists():
        warnings.warn(
            f"Prompts file not found at {prompts_path}, using built-in defaults.",
            UserWarning,
        )
        return dict(DEFAULT_PROMPTS)

    try:
        content = prompts_path.read_text()
        prompts = _parse_prompts_markdown(content)

        if not prompts:
            warnings.warn(
                f"Prompts file at {prompts_path} appears malformed, using built-in defaults.",
                UserWarning,
            )
            return dict(DEFAULT_PROMPTS)

        # Merge with defaults for any missing prompts
        result = dict(DEFAULT_PROMPTS)
        result.update(prompts)
        return result

    except OSError as e:
        warnings.warn(
            f"Failed to read prompts file: {e}, using built-in defaults.",
            UserWarning,
        )
        return dict(DEFAULT_PROMPTS)


def get_prompt(name: str, prompts: Optional[dict[str, str]] = None, **kwargs) -> str:
    """Get a specific prompt by name, optionally formatted with kwargs.

    Args:
        name: Prompt name (e.g., "advertisement_detection").
        prompts: Optional pre-loaded prompts dict. If None, loads prompts.
        **kwargs: Format arguments for the prompt template.

    Returns:
        Formatted prompt string.
    """
    if prompts is None:
        prompts = load_prompts()

    prompt = prompts.get(name, "")
    if not prompt:
        warnings.warn(f"Prompt '{name}' not found.", UserWarning)
        return ""

    if kwargs:
        return prompt.format(**kwargs)
    return prompt
