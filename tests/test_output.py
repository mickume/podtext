"""Unit tests for the output module.

Tests markdown generation functionality including frontmatter and content formatting.

Requirements: 4.4, 4.5, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from podtext.core.output import (
    _add_paragraph_breaks,
    _format_content,
    _format_frontmatter,
    generate_markdown,
    generate_markdown_string,
)
from podtext.services.claude import AnalysisResult
from podtext.services.rss import EpisodeInfo
from podtext.services.transcriber import TranscriptionResult


@pytest.fixture
def sample_episode() -> EpisodeInfo:
    """Create a sample episode for testing."""
    return EpisodeInfo(
        index=1,
        title="Test Episode Title",
        pub_date=datetime(2024, 1, 15, 10, 30, 0),
        media_url="https://example.com/episode1.mp3",
    )


@pytest.fixture
def sample_transcription() -> TranscriptionResult:
    """Create a sample transcription for testing."""
    return TranscriptionResult(
        text="Hello and welcome to the show. Today we discuss testing. It's very important.",
        paragraphs=[
            "Hello and welcome to the show.",
            "Today we discuss testing.",
            "It's very important.",
        ],
        language="en",
    )


@pytest.fixture
def sample_analysis() -> AnalysisResult:
    """Create a sample analysis result for testing."""
    return AnalysisResult(
        summary="A test episode about software testing practices.",
        topics=["Software testing fundamentals", "Unit testing best practices"],
        keywords=["testing", "software", "unit tests", "quality"],
        ad_markers=[],
    )


@pytest.fixture
def analysis_with_ads() -> AnalysisResult:
    """Create an analysis result with advertisement markers."""
    return AnalysisResult(
        summary="Episode with ads.",
        topics=["Main topic"],
        keywords=["keyword"],
        ad_markers=[(31, 60)],  # Marks "Today we discuss testing." as ad
    )


class TestFormatFrontmatter:
    """Tests for _format_frontmatter helper function."""

    def test_basic_frontmatter_structure(self, sample_episode, sample_analysis):
        """Frontmatter has correct YAML delimiters."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        assert result.startswith("---\n")
        assert result.endswith("---\n")

    def test_contains_title(self, sample_episode, sample_analysis):
        """Validates: Requirement 4.5 - Title in frontmatter."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        # Parse YAML to verify
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert data["title"] == "Test Episode Title"

    def test_contains_pub_date(self, sample_episode, sample_analysis):
        """Validates: Requirement 4.5 - Publication date in frontmatter."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert data["pub_date"] == "2024-01-15"

    def test_summary_not_in_frontmatter(self, sample_episode, sample_analysis):
        """Summary is no longer included in frontmatter (moved to main content)."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "summary" not in data

    def test_contains_topics(self, sample_episode, sample_analysis):
        """Validates: Requirement 7.3 - Topics in frontmatter."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "topics" in data
        assert len(data["topics"]) == 2
        assert "Software testing fundamentals" in data["topics"]

    def test_contains_keywords(self, sample_episode, sample_analysis):
        """Validates: Requirement 7.4 - Keywords in frontmatter."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "keywords" in data
        assert "testing" in data["keywords"]
        assert "software" in data["keywords"]

    def test_includes_podcast_name(self, sample_episode, sample_analysis):
        """Podcast name is included when provided."""
        result = _format_frontmatter(sample_episode, sample_analysis, "My Podcast")
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert data["podcast"] == "My Podcast"

    def test_omits_podcast_name_when_empty(self, sample_episode, sample_analysis):
        """Podcast name is omitted when not provided."""
        result = _format_frontmatter(sample_episode, sample_analysis, "")
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "podcast" not in data

    def test_omits_empty_summary(self, sample_episode):
        """Empty summary is omitted from frontmatter."""
        analysis = AnalysisResult(summary="", topics=[], keywords=[], ad_markers=[])
        result = _format_frontmatter(sample_episode, analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "summary" not in data

    def test_omits_empty_topics(self, sample_episode):
        """Empty topics list is omitted from frontmatter."""
        analysis = AnalysisResult(summary="Test", topics=[], keywords=["kw"], ad_markers=[])
        result = _format_frontmatter(sample_episode, analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "topics" not in data

    def test_omits_empty_keywords(self, sample_episode):
        """Empty keywords list is omitted from frontmatter."""
        analysis = AnalysisResult(summary="Test", topics=["topic"], keywords=[], ad_markers=[])
        result = _format_frontmatter(sample_episode, analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "keywords" not in data

    def test_valid_yaml_output(self, sample_episode, sample_analysis):
        """Output is valid YAML that can be parsed."""
        result = _format_frontmatter(sample_episode, sample_analysis)
        yaml_content = result.strip("---\n")
        # Should not raise
        data = yaml.safe_load(yaml_content)
        assert isinstance(data, dict)

    def test_unicode_content(self, sample_analysis):
        """Unicode content is handled correctly."""
        episode = EpisodeInfo(
            index=1,
            title="Épisode avec accents: café, naïve",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/ep.mp3",
        )
        result = _format_frontmatter(episode, sample_analysis)
        yaml_content = result.strip("---\n")
        data = yaml.safe_load(yaml_content)
        assert "café" in data["title"]
        assert "naïve" in data["title"]


class TestFormatContent:
    """Tests for _format_content helper function."""

    def test_returns_paragraphs_without_ads(self, sample_transcription):
        """Content uses paragraphs when no ads present."""
        result = _format_content(sample_transcription, [])
        # Paragraphs should be joined with double newlines
        assert "Hello and welcome to the show." in result
        assert "Today we discuss testing." in result

    def test_includes_summary_section(self, sample_transcription):
        """Validates: Requirement 7.2 - Summary in main content."""
        result = _format_content(
            sample_transcription, [], summary="This is a test summary."
        )
        assert "## Summary" in result
        assert "This is a test summary." in result

    def test_summary_before_transcription(self, sample_transcription):
        """Summary appears before transcription content."""
        result = _format_content(
            sample_transcription, [], summary="Test summary"
        )
        summary_pos = result.find("## Summary")
        transcription_pos = result.find("Hello and welcome")
        assert summary_pos < transcription_pos

    def test_show_notes_after_summary(self, sample_transcription):
        """Show notes appear after summary but before transcription."""
        result = _format_content(
            sample_transcription,
            [],
            show_notes="<p>These are show notes</p>",
            summary="Test summary",
        )
        summary_pos = result.find("## Summary")
        show_notes_pos = result.find("## Show Notes")
        transcription_pos = result.find("## Transcription")
        assert summary_pos < show_notes_pos < transcription_pos

    def test_transcription_header_when_summary_present(self, sample_transcription):
        """Transcription section has header when summary is present."""
        result = _format_content(
            sample_transcription, [], summary="Test summary"
        )
        assert "## Transcription" in result

    def test_no_transcription_header_without_summary_or_notes(self, sample_transcription):
        """No transcription header when no summary or show notes."""
        result = _format_content(sample_transcription, [])
        assert "## Transcription" not in result
        assert "Hello and welcome to the show." in result

    def test_removes_advertisements(self):
        """Validates: Requirement 7.5 - Ads are marked in transcription."""
        transcription = TranscriptionResult(
            text="Hello. BUY NOW! Goodbye.",
            paragraphs=["Hello.", "BUY NOW!", "Goodbye."],
            language="en",
        )
        # Mark "BUY NOW! " as ad (positions 7-16)
        result = _format_content(transcription, [(7, 16)])
        assert "BUY NOW" not in result
        assert "ADVERTISEMENT WAS REMOVED" in result

    def test_preserves_non_ad_content(self, sample_transcription):
        """Non-advertisement content is preserved."""
        result = _format_content(sample_transcription, [])
        assert "Hello and welcome to the show." in result
        assert "Today we discuss testing." in result
        assert "It's very important." in result

    def test_empty_paragraphs_uses_text(self):
        """Falls back to text when paragraphs are empty."""
        transcription = TranscriptionResult(
            text="Just plain text here.",
            paragraphs=[],
            language="en",
        )
        result = _format_content(transcription, [])
        assert "Just plain text here." in result


class TestAddParagraphBreaks:
    """Tests for _add_paragraph_breaks helper function."""

    def test_empty_text(self):
        """Empty text returns empty string."""
        assert _add_paragraph_breaks("") == ""

    def test_single_line(self):
        """Single line text is returned as-is."""
        result = _add_paragraph_breaks("Single line of text.")
        assert result == "Single line of text."

    def test_multiple_lines(self):
        """Multiple lines are joined with double newlines."""
        text = "Line one.\nLine two.\nLine three."
        result = _add_paragraph_breaks(text)
        assert "\n\n" in result

    def test_filters_empty_lines(self):
        """Empty lines are filtered out."""
        text = "Line one.\n\n\nLine two."
        result = _add_paragraph_breaks(text)
        # Should not have excessive newlines
        assert "\n\n\n" not in result


class TestGenerateMarkdownString:
    """Tests for generate_markdown_string function."""

    def test_combines_frontmatter_and_content(
        self, sample_episode, sample_transcription, sample_analysis
    ):
        """Output contains both frontmatter and content."""
        result = generate_markdown_string(sample_episode, sample_transcription, sample_analysis)
        # Has frontmatter
        assert result.startswith("---\n")
        assert "title:" in result
        # Has summary in content
        assert "## Summary" in result
        # Has transcription content
        assert "Hello and welcome to the show." in result

    def test_frontmatter_before_content(
        self, sample_episode, sample_transcription, sample_analysis
    ):
        """Frontmatter appears before content."""
        result = generate_markdown_string(sample_episode, sample_transcription, sample_analysis)
        frontmatter_end = result.rfind("---\n") + 4
        summary_start = result.find("## Summary")
        assert frontmatter_end < summary_start

    def test_includes_all_analysis_results(
        self, sample_episode, sample_transcription, sample_analysis
    ):
        """Validates: Requirement 7.6 - All analysis results included."""
        result = generate_markdown_string(sample_episode, sample_transcription, sample_analysis)
        # Extract and parse frontmatter
        lines = result.split("\n")
        yaml_lines = []
        in_frontmatter = False
        for line in lines:
            if line == "---":
                if in_frontmatter:
                    break
                in_frontmatter = True
                continue
            if in_frontmatter:
                yaml_lines.append(line)

        yaml_content = "\n".join(yaml_lines)
        data = yaml.safe_load(yaml_content)

        # Topics and keywords should be in frontmatter
        assert "topics" in data
        assert "keywords" in data
        
        # Summary should be in main content, not frontmatter
        assert "summary" not in data
        assert "## Summary" in result
        assert "A test episode about software testing practices." in result

    def test_with_podcast_name(self, sample_episode, sample_transcription, sample_analysis):
        """Podcast name is included when provided."""
        result = generate_markdown_string(
            sample_episode, sample_transcription, sample_analysis, "Test Podcast"
        )
        assert "podcast:" in result
        assert "Test Podcast" in result


class TestGenerateMarkdown:
    """Tests for generate_markdown function."""

    def test_creates_file(self, sample_episode, sample_transcription, sample_analysis):
        """Validates: Requirement 4.4 - Generates markdown file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"
            generate_markdown(sample_episode, sample_transcription, sample_analysis, output_path)
            assert output_path.exists()

    def test_file_content_matches_string(
        self, sample_episode, sample_transcription, sample_analysis
    ):
        """File content matches string generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"
            generate_markdown(sample_episode, sample_transcription, sample_analysis, output_path)

            file_content = output_path.read_text(encoding="utf-8")
            string_content = generate_markdown_string(
                sample_episode, sample_transcription, sample_analysis
            )

            assert file_content == string_content

    def test_creates_parent_directories(
        self, sample_episode, sample_transcription, sample_analysis
    ):
        """Parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dirs" / "output.md"
            generate_markdown(sample_episode, sample_transcription, sample_analysis, output_path)
            assert output_path.exists()

    def test_overwrites_existing_file(self, sample_episode, sample_transcription, sample_analysis):
        """Existing file is overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"
            output_path.write_text("old content")

            generate_markdown(sample_episode, sample_transcription, sample_analysis, output_path)

            content = output_path.read_text()
            assert "old content" not in content
            assert "title:" in content

    def test_utf8_encoding(self, sample_transcription, sample_analysis):
        """File is written with UTF-8 encoding."""
        episode = EpisodeInfo(
            index=1,
            title="日本語タイトル",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/ep.mp3",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"
            generate_markdown(episode, sample_transcription, sample_analysis, output_path)

            content = output_path.read_text(encoding="utf-8")
            assert "日本語タイトル" in content

    def test_with_advertisement_markers(
        self, sample_episode, sample_transcription, analysis_with_ads
    ):
        """Validates: Requirement 7.5 - Sponsor content marked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"
            generate_markdown(sample_episode, sample_transcription, analysis_with_ads, output_path)

            content = output_path.read_text()
            assert "ADVERTISEMENT WAS REMOVED" in content


class TestMarkdownOutputCompleteness:
    """Integration tests for complete markdown output.

    Validates: Requirements 4.4, 4.5, 7.6
    """

    def test_complete_output_structure(self, sample_episode, sample_transcription, sample_analysis):
        """Output has complete structure with all required elements."""
        result = generate_markdown_string(
            sample_episode, sample_transcription, sample_analysis, "Test Podcast"
        )

        # Frontmatter structure
        assert result.startswith("---\n")
        assert result.count("---") >= 2

        # Required frontmatter fields (Requirement 4.5)
        assert "title:" in result
        assert "pub_date:" in result

        # Analysis results (Requirement 7.6)
        # Summary now in main content, not frontmatter
        assert "## Summary" in result
        assert "topics:" in result
        assert "keywords:" in result

        # Content present (Requirement 4.4)
        assert "Hello and welcome" in result

    def test_parseable_yaml_frontmatter(
        self, sample_episode, sample_transcription, sample_analysis
    ):
        """Frontmatter is valid, parseable YAML."""
        result = generate_markdown_string(sample_episode, sample_transcription, sample_analysis)

        # Extract frontmatter
        parts = result.split("---")
        assert len(parts) >= 3
        yaml_content = parts[1].strip()

        # Should parse without error
        data = yaml.safe_load(yaml_content)
        assert isinstance(data, dict)
        assert "title" in data
        assert "pub_date" in data
        # Summary should not be in frontmatter anymore
        assert "summary" not in data
