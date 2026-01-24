"""Markdown output generation for transcripts."""

import re
from pathlib import Path

import yaml

from podtext.config.manager import Config
from podtext.models.podcast import Episode
from podtext.models.transcript import Analysis, Transcript


class MarkdownWriter:
    """Generates markdown files for transcribed episodes."""

    def __init__(self, config: Config):
        """Initialize the markdown writer.

        Args:
            config: Application configuration
        """
        self.config = config
        self.output_dir = Path(config.output_dir)

    def write(
        self,
        podcast_name: str,
        episode: Episode,
        transcript: Transcript,
        analysis: Analysis | None = None,
    ) -> Path:
        """Write a transcript to a markdown file.

        Args:
            podcast_name: Name of the podcast
            episode: Episode metadata
            transcript: Transcription data
            analysis: Optional analysis data

        Returns:
            Path to the written file
        """
        # Create output directory
        podcast_dir = self.output_dir / self._sanitize_filename(podcast_name)
        podcast_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = self._sanitize_filename(episode.title) + ".md"
        output_path = podcast_dir / filename

        # Generate content
        content = self._generate_content(podcast_name, episode, transcript, analysis)

        # Write file
        output_path.write_text(content, encoding="utf-8")

        return output_path

    def _generate_content(
        self,
        podcast_name: str,
        episode: Episode,
        transcript: Transcript,
        analysis: Analysis | None,
    ) -> str:
        """Generate the full markdown content."""
        parts = []

        # Generate frontmatter
        frontmatter = self._generate_frontmatter(podcast_name, episode, analysis)
        parts.append(frontmatter)

        # Add main title
        parts.append(f"# {episode.title}\n")

        # Add analysis section if available
        if analysis and analysis.summary:
            parts.append("## Summary\n")
            parts.append(analysis.summary + "\n")

            if analysis.topics:
                parts.append("## Topics\n")
                for topic in analysis.topics:
                    parts.append(f"- {topic}")
                parts.append("")

        # Add transcript
        parts.append("## Transcript\n")

        # Get transcript text, optionally with ads removed
        text = transcript.get_text_with_paragraphs()
        if analysis and analysis.ad_segments:
            from podtext.services.analyzer import AnalyzerService

            # Remove high-confidence ads
            text = AnalyzerService.remove_advertising(
                AnalyzerService, text, analysis.ad_segments
            )

        parts.append(text)

        return "\n".join(parts)

    def _generate_frontmatter(
        self,
        podcast_name: str,
        episode: Episode,
        analysis: Analysis | None,
    ) -> str:
        """Generate YAML frontmatter."""
        data: dict = {
            "title": episode.title,
            "podcast": podcast_name,
            "date": episode.pub_date.isoformat(),
            "language": episode.language or "en",
        }

        if episode.duration:
            data["duration"] = episode.duration_formatted

        if analysis:
            if analysis.keywords:
                data["keywords"] = analysis.keywords
            if analysis.topics:
                data["topics"] = [t[:100] for t in analysis.topics]  # Truncate long topics

        # Generate YAML with proper formatting
        yaml_content = yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return f"---\n{yaml_content}---\n"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "", name)
        # Replace multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", sanitized)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(" .")
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100].rsplit(" ", 1)[0]
        # Fallback if empty
        if not sanitized:
            sanitized = "untitled"
        return sanitized

    def get_output_path(self, podcast_name: str, episode_title: str) -> Path:
        """Get the expected output path for an episode.

        Args:
            podcast_name: Name of the podcast
            episode_title: Title of the episode

        Returns:
            Expected output file path
        """
        podcast_dir = self.output_dir / self._sanitize_filename(podcast_name)
        filename = self._sanitize_filename(episode_title) + ".md"
        return podcast_dir / filename
