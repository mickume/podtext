"""Tests for output generation.

Feature: podtext
Property 8: Markdown Output Completeness
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from pathlib import Path
import yaml

from podtext.output import (
    generate_frontmatter,
    generate_markdown,
    generate_output_filename,
)
from podtext.models import EpisodeInfo, TranscriptionResult, AnalysisResult


@pytest.fixture
def sample_episode():
    """Create a sample episode for testing."""
    return EpisodeInfo(
        index=1,
        title="Test Episode",
        pub_date=datetime(2024, 1, 15, 12, 0, 0),
        media_url="https://example.com/episode.mp3",
    )


@pytest.fixture
def sample_transcription():
    """Create a sample transcription for testing."""
    return TranscriptionResult(
        text="This is the full transcript text.",
        paragraphs=["First paragraph.", "Second paragraph."],
        language="en",
    )


@pytest.fixture
def sample_analysis():
    """Create a sample analysis for testing."""
    return AnalysisResult(
        summary="This is a summary of the episode.",
        topics=["Topic one", "Topic two"],
        keywords=["keyword1", "keyword2"],
    )


class TestGenerateFrontmatter:
    """Tests for frontmatter generation."""

    def test_basic_frontmatter(self, sample_episode, sample_analysis):
        """Generate basic frontmatter."""
        result = generate_frontmatter(sample_episode, sample_analysis)

        assert result.startswith("---\n")
        assert result.endswith("---\n")

        # Parse the YAML content
        yaml_content = result[4:-4]  # Remove delimiters
        parsed = yaml.safe_load(yaml_content)

        assert parsed["title"] == "Test Episode"
        assert parsed["pub_date"] == "2024-01-15"

    def test_frontmatter_with_podcast_name(self, sample_episode, sample_analysis):
        """Frontmatter includes podcast name when provided."""
        result = generate_frontmatter(sample_episode, sample_analysis, podcast_name="My Podcast")

        yaml_content = result[4:-4]
        parsed = yaml.safe_load(yaml_content)

        assert parsed["podcast"] == "My Podcast"

    def test_frontmatter_includes_analysis(self, sample_episode, sample_analysis):
        """Frontmatter includes analysis results."""
        result = generate_frontmatter(sample_episode, sample_analysis)

        yaml_content = result[4:-4]
        parsed = yaml.safe_load(yaml_content)

        assert parsed["summary"] == "This is a summary of the episode."
        assert parsed["topics"] == ["Topic one", "Topic two"]
        assert parsed["keywords"] == ["keyword1", "keyword2"]

    def test_frontmatter_empty_analysis(self, sample_episode):
        """Frontmatter handles empty analysis."""
        empty_analysis = AnalysisResult(summary="", topics=[], keywords=[])
        result = generate_frontmatter(sample_episode, empty_analysis)

        yaml_content = result[4:-4]
        parsed = yaml.safe_load(yaml_content)

        # Empty fields should not be included
        assert "summary" not in parsed
        assert "topics" not in parsed
        assert "keywords" not in parsed


class TestGenerateMarkdown:
    """Tests for markdown file generation."""

    def test_creates_file(self, temp_dir, sample_episode, sample_transcription, sample_analysis):
        """Generate creates a file."""
        output_path = temp_dir / "output.md"

        result = generate_markdown(
            sample_episode, sample_transcription, sample_analysis, output_path
        )

        assert result.exists()
        assert result == output_path

    def test_creates_directory(self, temp_dir, sample_episode, sample_transcription, sample_analysis):
        """Generate creates output directory if needed."""
        output_path = temp_dir / "subdir" / "deep" / "output.md"

        result = generate_markdown(
            sample_episode, sample_transcription, sample_analysis, output_path
        )

        assert result.exists()
        assert result.parent.exists()

    def test_file_content(self, temp_dir, sample_episode, sample_transcription, sample_analysis):
        """Generated file contains frontmatter and content."""
        output_path = temp_dir / "output.md"

        generate_markdown(
            sample_episode, sample_transcription, sample_analysis, output_path
        )

        content = output_path.read_text()

        # Check frontmatter
        assert content.startswith("---\n")
        assert "title:" in content

        # Check content
        assert "First paragraph." in content
        assert "Second paragraph." in content


class TestGenerateOutputFilename:
    """Tests for filename generation."""

    def test_basic_filename(self, sample_episode):
        """Generate basic filename."""
        result = generate_output_filename(sample_episode)
        assert result == "2024-01-15-Test Episode.md"

    def test_sanitizes_special_characters(self):
        """Special characters are sanitized."""
        episode = EpisodeInfo(
            index=1,
            title="Episode: The \"Best\" One?",
            pub_date=datetime(2024, 1, 1),
            media_url="https://example.com/ep.mp3",
        )
        result = generate_output_filename(episode)

        assert ":" not in result
        assert '"' not in result
        assert "?" not in result

    def test_truncates_long_titles(self):
        """Long titles are truncated."""
        long_title = "A" * 200
        episode = EpisodeInfo(
            index=1,
            title=long_title,
            pub_date=datetime(2024, 1, 1),
            media_url="https://example.com/ep.mp3",
        )
        result = generate_output_filename(episode)

        # Should be date prefix + 100 chars + .md
        assert len(result) <= 120


class TestProperty8MarkdownOutputCompleteness:
    """Property 8: Markdown Output Completeness.

    For any EpisodeInfo and AnalysisResult, the generated markdown SHALL contain
    valid YAML frontmatter with title, pub_date, summary, topics, and keywords fields.

    Validates: Requirements 4.4, 4.5, 7.6
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        title=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
        day=st.integers(min_value=1, max_value=28),
        month=st.integers(min_value=1, max_value=12),
        year=st.integers(min_value=2000, max_value=2030),
    )
    def test_frontmatter_has_required_fields(self, title, day, month, year):
        """Frontmatter always contains title and pub_date."""
        episode = EpisodeInfo(
            index=1,
            title=title,
            pub_date=datetime(year, month, day),
            media_url="https://example.com/ep.mp3",
        )
        analysis = AnalysisResult(
            summary="Summary text",
            topics=["Topic 1"],
            keywords=["keyword"],
        )

        result = generate_frontmatter(episode, analysis)

        # Should have valid YAML
        assert result.startswith("---\n")
        assert result.endswith("---\n")

        yaml_content = result[4:-4]
        parsed = yaml.safe_load(yaml_content)

        # Required fields
        assert "title" in parsed
        assert "pub_date" in parsed
        assert parsed["title"] == title

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        summary=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"))),
        topics=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N"))),
            min_size=1, max_size=5
        ),
        keywords=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))),
            min_size=1, max_size=10
        ),
    )
    def test_frontmatter_includes_analysis_fields(self, summary, topics, keywords):
        """Frontmatter includes analysis fields when present."""
        episode = EpisodeInfo(
            index=1,
            title="Test Episode",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/ep.mp3",
        )
        analysis = AnalysisResult(
            summary=summary,
            topics=topics,
            keywords=keywords,
        )

        result = generate_frontmatter(episode, analysis)

        yaml_content = result[4:-4]
        parsed = yaml.safe_load(yaml_content)

        # Analysis fields should be present
        assert parsed["summary"] == summary
        assert parsed["topics"] == topics
        assert parsed["keywords"] == keywords

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        text=st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"))),
    )
    def test_markdown_contains_transcription(self, temp_dir, text):
        """Generated markdown contains transcription text."""
        episode = EpisodeInfo(
            index=1,
            title="Test",
            pub_date=datetime(2024, 1, 1),
            media_url="https://example.com/ep.mp3",
        )
        transcription = TranscriptionResult(
            text=text,
            paragraphs=[text],
            language="en",
        )
        analysis = AnalysisResult(summary="", topics=[], keywords=[])

        output_path = temp_dir / f"test_{hash(text) % 10000}.md"
        generate_markdown(episode, transcription, analysis, output_path)

        content = output_path.read_text()

        # Text should be in the file
        assert text in content
