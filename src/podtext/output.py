"""Markdown output generation for transcripts."""

from datetime import datetime
from pathlib import Path

import yaml

from podtext.models import AnalysisResult, EpisodeInfo, TranscriptionResult
from podtext.processor import remove_advertisements


def generate_frontmatter(
    episode: EpisodeInfo,
    analysis: AnalysisResult | None,
) -> dict:
    """
    Generate YAML frontmatter data for the output file.

    Args:
        episode: Episode information
        analysis: Optional analysis results

    Returns:
        Dictionary suitable for YAML serialization
    """
    frontmatter = {
        "title": episode.title,
        "pub_date": episode.pub_date.strftime("%Y-%m-%d"),
        "podcast": episode.podcast_title,
    }

    if analysis:
        frontmatter["summary"] = analysis.summary
        frontmatter["topics"] = analysis.topics
        frontmatter["keywords"] = analysis.keywords

    return frontmatter


def format_paragraphs(paragraphs: list[str]) -> str:
    """
    Format transcription paragraphs for markdown output.

    Args:
        paragraphs: List of paragraph strings

    Returns:
        Formatted markdown text with double newlines between paragraphs
    """
    return "\n\n".join(p.strip() for p in paragraphs if p.strip())


def generate_markdown(
    episode: EpisodeInfo,
    transcription: TranscriptionResult,
    analysis: AnalysisResult | None,
    output_path: Path | str,
) -> Path:
    """
    Generate a markdown file with frontmatter and transcription.

    Args:
        episode: Episode information
        transcription: Transcription results
        analysis: Optional AI analysis results
        output_path: Path for the output file

    Returns:
        Path to the created file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate frontmatter
    frontmatter = generate_frontmatter(episode, analysis)

    # Format the transcript text
    if transcription.paragraphs:
        text = format_paragraphs(transcription.paragraphs)
    else:
        text = transcription.text

    # Remove advertisements if analysis identified them
    if analysis and analysis.ad_markers:
        text = remove_advertisements(text, analysis.ad_markers)

    # Build the markdown content
    frontmatter_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    content = f"""---
{frontmatter_yaml.strip()}
---

{text}
"""

    # Write the file
    output_path.write_text(content, encoding="utf-8")

    return output_path


def generate_output_filename(episode: EpisodeInfo) -> str:
    """
    Generate a filename for the output file.

    Args:
        episode: Episode information

    Returns:
        Sanitized filename with .md extension
    """
    # Sanitize the title for use as filename
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in episode.title
    )
    safe_title = safe_title.strip().replace(" ", "_")[:100]

    date_str = episode.pub_date.strftime("%Y%m%d")

    return f"{date_str}_{safe_title}.md"


def validate_markdown_output(output_path: Path) -> bool:
    """
    Validate that the output file has correct structure.

    Checks for:
    1. YAML frontmatter delimiters
    2. Required frontmatter fields

    Args:
        output_path: Path to the markdown file

    Returns:
        True if validation passes
    """
    if not output_path.exists():
        return False

    content = output_path.read_text(encoding="utf-8")

    # Check for frontmatter delimiters
    if not content.startswith("---\n"):
        return False

    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return False

    # Parse frontmatter
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return False

    # Check required fields
    required_fields = ["title", "pub_date"]
    for field in required_fields:
        if field not in frontmatter:
            return False

    return True
