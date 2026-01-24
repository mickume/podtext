"""Tests for markdown output generation."""

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from podtext.config.manager import Config
from podtext.models.podcast import Episode
from podtext.models.transcript import Analysis, Transcript
from podtext.output.markdown import MarkdownWriter


class TestMarkdownWriter:
    """Tests for MarkdownWriter."""

    def test_write_creates_file(self, tmp_path):
        """Test that write creates markdown file."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        episode = Episode(
            title="Test Episode",
            pub_date=datetime(2024, 3, 20, 10, 0, 0),
            media_url="https://example.com/ep.mp3",
            language="en",
        )
        transcript = Transcript(text="This is the transcript.")

        result = writer.write("Test Podcast", episode, transcript)

        assert result.exists()
        assert result.name == "Test Episode.md"
        assert result.parent.name == "Test Podcast"

    def test_write_includes_frontmatter(self, tmp_path):
        """Test that output includes YAML frontmatter."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        episode = Episode(
            title="My Episode",
            pub_date=datetime(2024, 3, 20),
            media_url="https://example.com/ep.mp3",
            duration=3600,
        )
        transcript = Transcript(text="Content.")

        result = writer.write("My Podcast", episode, transcript)

        content = result.read_text()

        # Check frontmatter structure
        assert content.startswith("---\n")
        assert "---\n" in content[4:]

        # Parse frontmatter
        frontmatter_end = content.find("---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["title"] == "My Episode"
        assert frontmatter["podcast"] == "My Podcast"
        assert "2024-03-20" in frontmatter["date"]

    def test_write_includes_analysis(self, tmp_path):
        """Test that output includes analysis."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        episode = Episode(
            title="Episode",
            pub_date=datetime(2024, 3, 20),
            media_url="https://example.com/ep.mp3",
        )
        transcript = Transcript(text="Transcript content.")
        analysis = Analysis(
            summary="This is the summary.",
            topics=["Topic one", "Topic two"],
            keywords=["key1", "key2", "key3"],
        )

        result = writer.write("Podcast", episode, transcript, analysis)

        content = result.read_text()

        assert "## Summary" in content
        assert "This is the summary." in content
        assert "## Topics" in content
        assert "- Topic one" in content
        assert "- Topic two" in content

        # Keywords in frontmatter
        assert "key1" in content

    def test_write_includes_transcript(self, tmp_path):
        """Test that output includes transcript."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        episode = Episode(
            title="Episode",
            pub_date=datetime(2024, 3, 20),
            media_url="https://example.com/ep.mp3",
        )
        transcript = Transcript(
            text="Full transcript text here.",
            paragraphs=["Paragraph one.", "Paragraph two."],
        )

        result = writer.write("Podcast", episode, transcript)

        content = result.read_text()

        assert "## Transcript" in content
        assert "Paragraph one." in content
        assert "Paragraph two." in content

    def test_sanitize_filename(self, tmp_path):
        """Test filename sanitization."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        # Test various problematic characters
        assert writer._sanitize_filename('Test: Episode "1"') == "Test Episode 1"
        assert writer._sanitize_filename("Episode/Part\\2") == "EpisodePart2"
        assert writer._sanitize_filename("  Spaces  ") == "Spaces"
        assert writer._sanitize_filename("...dots...") == "dots"
        assert writer._sanitize_filename("") == "untitled"

    def test_sanitize_filename_length_limit(self, tmp_path):
        """Test filename length limiting."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        long_title = "A" * 150
        result = writer._sanitize_filename(long_title)

        assert len(result) <= 100

    def test_get_output_path(self, tmp_path):
        """Test output path generation."""
        config = Config(output_dir=str(tmp_path))
        writer = MarkdownWriter(config)

        path = writer.get_output_path("My Podcast", "Episode 1")

        assert path == tmp_path / "My Podcast" / "Episode 1.md"

    def test_write_creates_directories(self, tmp_path):
        """Test that write creates necessary directories."""
        output_dir = tmp_path / "nested" / "output"
        config = Config(output_dir=str(output_dir))
        writer = MarkdownWriter(config)

        episode = Episode(
            title="Episode",
            pub_date=datetime(2024, 3, 20),
            media_url="https://example.com/ep.mp3",
        )
        transcript = Transcript(text="Content.")

        result = writer.write("New Podcast", episode, transcript)

        assert result.exists()
        assert result.parent.exists()
