"""Markdown output generation service."""

import re
from pathlib import Path

from podtext.core.errors import OutputError
from podtext.core.models import EpisodeOutput


class OutputService:
    """Handles markdown file generation."""

    def __init__(self, output_dir: Path) -> None:
        """
        Initialize the output service.

        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, output: EpisodeOutput) -> Path:
        """
        Generate markdown file from episode output.

        Args:
            output: EpisodeOutput containing all data

        Returns:
            Path to the generated file

        Raises:
            OutputError: If file generation fails
        """
        filename = self.generate_filename(
            output.podcast_title,
            output.episode.title,
        )
        output_path = self.output_dir / filename

        try:
            content = self._generate_content(output)
            output_path.write_text(content)
        except OSError as e:
            raise OutputError(f"Failed to write output file: {e}") from e

        return output_path

    def generate_filename(
        self,
        podcast_title: str,
        episode_title: str,
        max_length: int = 50,
    ) -> str:
        """
        Generate a truncated, safe filename.

        Args:
            podcast_title: Title of the podcast
            episode_title: Title of the episode
            max_length: Maximum filename length (default 50)

        Returns:
            Sanitized filename with .md extension
        """
        # Sanitize titles
        podcast = self._sanitize_for_filename(podcast_title)
        episode = self._sanitize_for_filename(episode_title)

        # Combine
        combined = f"{podcast}-{episode}"

        # Truncate if needed (leave room for .md)
        if len(combined) > max_length - 3:
            combined = combined[: max_length - 3]
            # Don't end with a dash or space
            combined = combined.rstrip("- ")

        return f"{combined}.md"

    def _sanitize_for_filename(self, text: str) -> str:
        """Sanitize text for use in filename."""
        # Remove/replace problematic characters
        text = re.sub(r'[<>:"/\\|?*]', "", text)
        # Replace spaces and multiple dashes
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"-+", "-", text)
        # Remove leading/trailing dashes
        text = text.strip("-")
        # Lowercase for consistency
        return text.lower()

    def _generate_content(self, output: EpisodeOutput) -> str:
        """Generate the full markdown content."""
        lines: list[str] = []

        # YAML frontmatter
        lines.append("---")
        lines.append(f"title: \"{self._escape_yaml(output.episode.title)}\"")
        lines.append(f"podcast: \"{self._escape_yaml(output.podcast_title)}\"")
        lines.append(f"date: {output.episode.published.strftime('%Y-%m-%d')}")
        lines.append(f"keywords: [{', '.join(output.analysis.keywords)}]")
        lines.append(f"language: {output.transcript.language}")
        lines.append(f"duration: {self._format_duration(output.transcript.duration)}")
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {output.episode.title}")
        lines.append("")
        lines.append(f"**Podcast:** {output.podcast_title}")
        lines.append(f"**Published:** {output.episode.published.strftime('%B %d, %Y')}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(output.analysis.summary)
        lines.append("")

        # Topics
        lines.append("## Topics Covered")
        lines.append("")
        for topic in output.analysis.topics:
            lines.append(f"- {topic}")
        lines.append("")

        # Keywords
        lines.append("## Keywords")
        lines.append("")
        lines.append(", ".join(output.analysis.keywords))
        lines.append("")

        # Transcript
        lines.append("## Transcript")
        lines.append("")
        lines.append(self._format_transcript(output))
        lines.append("")

        return "\n".join(lines)

    def _format_transcript(self, output: EpisodeOutput) -> str:
        """Format the transcript with advertising markers."""
        # Build set of segment indices that are advertising
        ad_indices: set[int] = set()
        for block in output.analysis.advertising_blocks:
            for i in range(block.start_index, block.end_index + 1):
                ad_indices.add(i)

        result: list[str] = []
        in_ad_block = False

        for i, segment in enumerate(output.transcript.segments):
            if i in ad_indices:
                if not in_ad_block:
                    result.append("\n[ADVERTISING REMOVED]\n")
                    in_ad_block = True
            else:
                in_ad_block = False
                result.append(segment.text)

        return " ".join(result)

    @staticmethod
    def _escape_yaml(text: str) -> str:
        """Escape text for YAML string."""
        return text.replace('"', '\\"')

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
