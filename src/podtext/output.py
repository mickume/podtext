"""Output generation for Podtext.

Generates markdown files with YAML frontmatter from transcription results.
"""

from datetime import datetime
from pathlib import Path

import yaml

from .models import EpisodeInfo, TranscriptionResult, AnalysisResult
from .processor import format_paragraphs


def generate_frontmatter(
    episode: EpisodeInfo,
    analysis: AnalysisResult,
    podcast_name: str = "",
) -> str:
    """Generate YAML frontmatter for the markdown file.

    Args:
        episode: Episode information.
        analysis: Analysis results from Claude.
        podcast_name: Optional podcast name.

    Returns:
        YAML frontmatter string including delimiters.
    """
    frontmatter_data = {
        "title": episode.title,
        "pub_date": episode.pub_date.strftime("%Y-%m-%d"),
    }

    if podcast_name:
        frontmatter_data["podcast"] = podcast_name

    if analysis.summary:
        frontmatter_data["summary"] = analysis.summary

    if analysis.topics:
        frontmatter_data["topics"] = analysis.topics

    if analysis.keywords:
        frontmatter_data["keywords"] = analysis.keywords

    # Use safe_dump for proper YAML formatting
    yaml_content = yaml.safe_dump(
        frontmatter_data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    return f"---\n{yaml_content}---\n"


def generate_markdown(
    episode: EpisodeInfo,
    transcription: TranscriptionResult,
    analysis: AnalysisResult,
    output_path: Path,
    podcast_name: str = "",
) -> Path:
    """Generate a markdown file with transcription and analysis.

    Args:
        episode: Episode information.
        transcription: Transcription result.
        analysis: Analysis result from Claude.
        output_path: Path for the output file.
        podcast_name: Optional podcast name.

    Returns:
        Path to the generated markdown file.
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate frontmatter
    frontmatter = generate_frontmatter(episode, analysis, podcast_name)

    # Format content
    if transcription.paragraphs:
        content = format_paragraphs(transcription.paragraphs)
    else:
        content = transcription.text

    # Combine frontmatter and content
    full_content = f"{frontmatter}\n{content}\n"

    # Write file
    output_path.write_text(full_content)

    return output_path


def generate_output_filename(episode: EpisodeInfo) -> str:
    """Generate a filename for the output markdown file.

    Args:
        episode: Episode information.

    Returns:
        Sanitized filename string.
    """
    # Sanitize title for filename
    title = episode.title
    # Remove or replace problematic characters
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        title = title.replace(char, '-')

    # Limit length
    if len(title) > 100:
        title = title[:100]

    # Add date prefix
    date_str = episode.pub_date.strftime("%Y-%m-%d")

    return f"{date_str}-{title}.md"
