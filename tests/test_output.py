"""Tests for output service."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from podtext.core.models import (
    AdvertisingBlock,
    Analysis,
    Episode,
    EpisodeOutput,
    Segment,
    Transcript,
)
from podtext.services.output import OutputService


class TestFilenameGeneration:
    """Tests for filename generation."""

    def test_generate_filename_simple(self) -> None:
        """Test simple filename generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            filename = service.generate_filename(
                "My Podcast",
                "Episode One",
            )
            assert filename == "my-podcast-episode-one.md"

    def test_generate_filename_truncation(self) -> None:
        """Test filename truncation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            filename = service.generate_filename(
                "This Is A Very Long Podcast Name That Goes On",
                "And This Is A Very Long Episode Title That Also Goes On",
                max_length=50,
            )
            assert len(filename) <= 50
            assert filename.endswith(".md")

    def test_generate_filename_special_chars(self) -> None:
        """Test filename with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            filename = service.generate_filename(
                "My: Podcast?",
                'Episode "One"',
            )
            assert ":" not in filename
            assert "?" not in filename
            assert '"' not in filename

    def test_generate_filename_spaces(self) -> None:
        """Test filename with spaces converted to dashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            filename = service.generate_filename(
                "My Podcast",
                "Episode   One",  # Multiple spaces
            )
            assert "  " not in filename  # No double spaces
            assert "--" not in filename  # No double dashes (after conversion)


class TestMarkdownGeneration:
    """Tests for markdown content generation."""

    def test_generate_creates_file(self, sample_output: EpisodeOutput) -> None:
        """Test that generate creates a markdown file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            path = service.generate(sample_output)

            assert path.exists()
            assert path.suffix == ".md"

    def test_generate_content_has_frontmatter(
        self, sample_output: EpisodeOutput
    ) -> None:
        """Test that generated content has YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            path = service.generate(sample_output)

            content = path.read_text()
            assert content.startswith("---")
            assert "title:" in content
            assert "keywords:" in content

    def test_generate_content_has_sections(
        self, sample_output: EpisodeOutput
    ) -> None:
        """Test that generated content has all sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            path = service.generate(sample_output)

            content = path.read_text()
            assert "## Summary" in content
            assert "## Topics Covered" in content
            assert "## Keywords" in content
            assert "## Transcript" in content

    def test_generate_with_advertising_markers(self) -> None:
        """Test that advertising blocks are marked."""
        segments = [
            Segment(text="Hello", start=0.0, end=1.0),
            Segment(text="Buy our product", start=1.0, end=2.0),
            Segment(text="Back to content", start=2.0, end=3.0),
        ]
        transcript = Transcript(segments=segments, language="en", duration=3.0)
        analysis = Analysis(
            summary="Test",
            topics=["Topic"],
            keywords=["keyword"],
            advertising_blocks=[
                AdvertisingBlock(start_index=1, end_index=1, confidence=0.95)
            ],
        )
        episode = Episode(
            index=1,
            title="Test",
            published=datetime.now(UTC),
            media_url="https://example.com/test.mp3",
        )
        output = EpisodeOutput(
            podcast_title="Test Podcast",
            episode=episode,
            transcript=transcript,
            analysis=analysis,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            service = OutputService(Path(tmpdir))
            path = service.generate(output)

            content = path.read_text()
            assert "[ADVERTISING REMOVED]" in content
            assert "Hello" in content
            assert "Back to content" in content
            # The advertising text should not be in the output
            assert "Buy our product" not in content


class TestDurationFormatting:
    """Tests for duration formatting."""

    def test_format_duration_seconds_only(self) -> None:
        """Test formatting duration under a minute."""
        result = OutputService._format_duration(45.0)
        assert result == "0:45"

    def test_format_duration_minutes(self) -> None:
        """Test formatting duration in minutes."""
        result = OutputService._format_duration(125.0)
        assert result == "2:05"

    def test_format_duration_hours(self) -> None:
        """Test formatting duration with hours."""
        result = OutputService._format_duration(3725.0)
        assert result == "1:02:05"


@pytest.fixture
def sample_output() -> EpisodeOutput:
    """Create a sample episode output for testing."""
    segments = [
        Segment(text="Hello and welcome.", start=0.0, end=2.0),
        Segment(text="Today we discuss testing.", start=2.0, end=4.0),
    ]
    transcript = Transcript(segments=segments, language="en", duration=4.0)
    analysis = Analysis(
        summary="This is a test episode.",
        topics=["Testing", "Development"],
        keywords=["test", "python"],
        advertising_blocks=[],
    )
    episode = Episode(
        index=1,
        title="Test Episode",
        published=datetime(2024, 1, 15, tzinfo=UTC),
        media_url="https://example.com/test.mp3",
    )
    return EpisodeOutput(
        podcast_title="Test Podcast",
        episode=episode,
        transcript=transcript,
        analysis=analysis,
    )
