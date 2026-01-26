"""Markdown output generator for Podtext.

Generates markdown files with YAML frontmatter containing episode metadata
and analysis results, followed by the transcribed text with paragraph formatting.

Requirements: 4.4, 4.5, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from podtext.services.claude import AnalysisResult
    from podtext.services.rss import EpisodeInfo
    from podtext.services.transcriber import TranscriptionResult

from podtext.core.processor import convert_html_to_markdown, remove_advertisements

# Maximum length for show notes before truncation
MAX_SHOW_NOTES_LENGTH = 50000


def _format_frontmatter(
    episode: EpisodeInfo,
    analysis: AnalysisResult,
    podcast_name: str = "",
) -> str:
    """Generate YAML frontmatter from episode and analysis data.

    Creates a YAML block containing:
    - title: Episode title
    - pub_date: Publication date in ISO format
    - podcast: Podcast name (if provided)
    - feed_url: RSS feed URL (if available)
    - media_url: Episode media file URL
    - topics: List of topics covered
    - keywords: List of relevant keywords

    Note: Summary is no longer included in frontmatter (moved to main content).

    Args:
        episode: Episode information from RSS feed.
        analysis: Analysis results from Claude API.
        podcast_name: Optional podcast name to include.

    Returns:
        YAML frontmatter string with delimiters.

    Validates: Requirements 4.5, 7.3, 7.4, 7.6
    """
    frontmatter_data: dict[str, str | list[str]] = {
        "title": episode.title,
        "pub_date": episode.pub_date.strftime("%Y-%m-%d"),
    }

    # Add podcast name if provided
    if podcast_name:
        frontmatter_data["podcast"] = podcast_name

    # Add feed_url if available (Requirement: enhanced-metadata 1.1, 1.2)
    if episode.feed_url:
        frontmatter_data["feed_url"] = episode.feed_url

    # Add media_url (always present, Requirement: enhanced-metadata 2.1, 2.2)
    frontmatter_data["media_url"] = episode.media_url

    # Add analysis results (Requirements 7.3, 7.4, 7.6)
    # Note: Summary is now added to main content instead of frontmatter
    if analysis.topics:
        frontmatter_data["topics"] = analysis.topics

    if analysis.keywords:
        frontmatter_data["keywords"] = analysis.keywords

    # Generate YAML with proper formatting
    # Use default_flow_style=False for readable multi-line output
    yaml_content = yaml.dump(
        frontmatter_data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=80,
    )

    return f"---\n{yaml_content}---\n"


def _format_content(
    transcription: TranscriptionResult,
    ad_markers: list[tuple[int, int]],
    show_notes: str = "",
    summary: str = "",
) -> str:
    """Format transcription content with summary, show notes, paragraph breaks, and ad markers.

    Processes the transcription text to:
    1. Add summary section at the beginning (if available)
    2. Add show notes section (if available)
    3. Remove detected advertisements and insert markers
    4. Format paragraphs with proper spacing

    Args:
        transcription: Transcription result with text and paragraphs.
        ad_markers: List of (start, end) positions for advertisements.
        show_notes: Optional show notes content to prepend.
        summary: Optional AI-generated summary to prepend.

    Returns:
        Formatted content string with summary, show notes, paragraphs, and ad markers.

    Validates: Requirements 4.4, 7.2, 7.5
    """
    content_parts = []

    # Add summary section if available (Requirement 7.2)
    if summary and summary.strip():
        content_parts.append(f"## Summary\n\n{summary.strip()}")

    # Add show notes if available
    formatted_show_notes = _format_show_notes(show_notes)
    if formatted_show_notes:
        content_parts.append(formatted_show_notes)

    # Process transcription content
    if transcription.paragraphs:
        # Process advertisement removal on each paragraph if needed
        if ad_markers:
            # For ad markers, we need to work with the full text
            processed_text = remove_advertisements(transcription.text, ad_markers)
            transcription_content = _add_paragraph_breaks(processed_text)
        else:
            # Use original paragraphs with double newlines for readability
            transcription_content = "\n\n".join(transcription.paragraphs)
    else:
        # No paragraphs available, process the raw text
        processed_text = remove_advertisements(transcription.text, ad_markers)
        transcription_content = _add_paragraph_breaks(processed_text)

    # Add transcription section header and content
    if content_parts:
        # If we have summary or show notes, add a header for the transcription
        content_parts.append(f"## Transcription\n\n{transcription_content}")
    else:
        # No summary or show notes, just add the transcription directly
        content_parts.append(transcription_content)

    return "\n\n".join(content_parts)


def _format_show_notes(show_notes: str, max_length: int = MAX_SHOW_NOTES_LENGTH) -> str:
    """Format show notes for markdown output.

    Converts HTML show notes to markdown and adds a section heading.
    Truncates if content exceeds max_length.

    Args:
        show_notes: Raw show notes content (may be HTML).
        max_length: Maximum character length before truncation.

    Returns:
        Formatted show notes section, or empty string if no notes.

    Validates: Requirements 2.1, 2.2, 2.3, 4.2
    """
    if not show_notes or not show_notes.strip():
        return ""

    # Convert HTML to markdown
    markdown_content = convert_html_to_markdown(show_notes)

    if not markdown_content or not markdown_content.strip():
        return ""

    # Truncate if too long
    if len(markdown_content) > max_length:
        markdown_content = markdown_content[:max_length]
        # Try to truncate at a word boundary
        last_space = markdown_content.rfind(" ")
        if last_space > max_length - 100:
            markdown_content = markdown_content[:last_space]
        markdown_content += "\n\n*[Show notes truncated due to length]*"

    return f"## Show Notes\n\n{markdown_content}"


def _add_paragraph_breaks(text: str) -> str:
    """Add paragraph breaks to text based on sentence patterns.

    Adds double newlines after groups of sentences to improve readability.
    Groups approximately 3-5 sentences per paragraph.

    Args:
        text: The text to format.

    Returns:
        Text with paragraph breaks added.
    """
    if not text:
        return text

    # If text has single newlines, convert them to paragraph breaks
    if "\n" in text:
        lines = text.split("\n")
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if non_empty_lines:
            return "\n\n".join(non_empty_lines)
        return text

    # No newlines - split text into sentences and group them into paragraphs
    import re

    # Split on sentence-ending punctuation followed by space
    sentences = re.split(r"(?<=[.!?])\s+", text)

    if len(sentences) <= 1:
        return text

    paragraphs = []
    current_paragraph = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        current_paragraph.append(sentence)

        # Create paragraph breaks every 4-5 sentences
        if len(current_paragraph) >= 4:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []

    # Add remaining sentences as final paragraph
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return "\n\n".join(paragraphs)


def generate_markdown(
    episode: EpisodeInfo,
    transcription: TranscriptionResult,
    analysis: AnalysisResult,
    output_path: Path,
    podcast_name: str = "",
) -> None:
    """Generate a markdown file with frontmatter and transcribed content.

    Creates a markdown file containing:
    - YAML frontmatter with episode metadata and analysis results (topics, keywords)
    - Summary section (if available from AI analysis)
    - Show notes section (if available from RSS feed)
    - Transcribed text with paragraph formatting
    - Advertisement removal markers where ads were detected

    The output format follows the structure:
    ```markdown
    ---
    title: "Episode Title"
    pub_date: "2024-01-15"
    podcast: "Podcast Name"
    topics:
      - "Topic one sentence"
      - "Topic two sentence"
    keywords:
      - keyword1
      - keyword2
    ---

    ## Summary

    AI-generated summary...

    ## Show Notes

    Show notes from RSS feed...

    ## Transcription

    Transcribed content with paragraphs...

    [ADVERTISEMENT WAS REMOVED]

    More content...
    ```

    Args:
        episode: Episode information from RSS feed.
        transcription: Transcription result with text and paragraphs.
        analysis: Analysis results from Claude API.
        output_path: Path where the markdown file will be written.
        podcast_name: Optional podcast name to include in frontmatter.

    Validates: Requirements 4.4, 4.5, 7.2, 7.3, 7.4, 7.5, 7.6

    Example:
        >>> from pathlib import Path
        >>> from datetime import datetime
        >>> episode = EpisodeInfo(
        ...     index=1,
        ...     title="My Episode",
        ...     pub_date=datetime(2024, 1, 15),
        ...     media_url="https://example.com/ep1.mp3"
        ... )
        >>> transcription = TranscriptionResult(
        ...     text="Hello world. This is a test.",
        ...     paragraphs=["Hello world.", "This is a test."],
        ...     language="en"
        ... )
        >>> analysis = AnalysisResult(
        ...     summary="A test episode.",
        ...     topics=["Testing"],
        ...     keywords=["test", "hello"],
        ...     ad_markers=[]
        ... )
        >>> generate_markdown(episode, transcription, analysis, Path("output.md"))
    """
    # Generate frontmatter (without summary)
    frontmatter = _format_frontmatter(episode, analysis, podcast_name)

    # Format content with summary, show notes, and ad removal
    content = _format_content(
        transcription,
        analysis.ad_markers,
        show_notes=episode.show_notes,
        summary=analysis.summary,
    )

    # Combine frontmatter and content
    markdown_output = f"{frontmatter}\n{content}\n"

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    output_path.write_text(markdown_output, encoding="utf-8")


def generate_markdown_string(
    episode: EpisodeInfo,
    transcription: TranscriptionResult,
    analysis: AnalysisResult,
    podcast_name: str = "",
) -> str:
    """Generate markdown content as a string without writing to file.

    Useful for testing or when the output needs to be processed further
    before writing.

    Args:
        episode: Episode information from RSS feed.
        transcription: Transcription result with text and paragraphs.
        analysis: Analysis results from Claude API.
        podcast_name: Optional podcast name to include in frontmatter.

    Returns:
        Complete markdown string with frontmatter and content.

    Validates: Requirements 4.4, 4.5, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    # Generate frontmatter (without summary)
    frontmatter = _format_frontmatter(episode, analysis, podcast_name)

    # Format content with summary, show notes, and ad removal
    content = _format_content(
        transcription,
        analysis.ad_markers,
        show_notes=episode.show_notes,
        summary=analysis.summary,
    )

    # Combine frontmatter and content
    return f"{frontmatter}\n{content}\n"
