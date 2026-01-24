"""Tests for output generation module.

Feature: podtext
Property tests verify universal properties across generated inputs.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

from podtext.models import AnalysisResult, EpisodeInfo, TranscriptionResult
from podtext.output import (
    format_paragraphs,
    generate_frontmatter,
    generate_markdown,
    generate_output_filename,
    validate_markdown_output,
)
from podtext.processor import (
    AD_REMOVED_MARKER,
    count_removed_ads,
    remove_advertisements,
    validate_ad_removal,
)


# Strategies for generating test data
text_strategy = st.text(
    min_size=1,
    max_size=500,
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
)
title_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
)


def create_episode(title: str = "Test Episode") -> EpisodeInfo:
    """Create a test episode."""
    return EpisodeInfo(
        index=1,
        title=title,
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/audio.mp3",
        podcast_title="Test Podcast",
    )


def create_transcription(text: str = "Hello world.") -> TranscriptionResult:
    """Create a test transcription."""
    return TranscriptionResult(
        text=text,
        paragraphs=[text],
        language="en",
    )


def create_analysis(
    summary: str = "A test summary.",
    topics: list[str] | None = None,
    keywords: list[str] | None = None,
    ad_markers: list[tuple[int, int]] | None = None,
) -> AnalysisResult:
    """Create a test analysis result."""
    return AnalysisResult(
        summary=summary,
        topics=topics or ["Topic 1"],
        keywords=keywords or ["keyword1", "keyword2"],
        ad_markers=ad_markers or [],
    )


class TestMarkdownOutputCompleteness:
    """
    Property 8: Markdown Output Completeness

    For any EpisodeInfo and AnalysisResult, the generated markdown
    SHALL contain valid YAML frontmatter with title, pub_date, summary,
    topics, and keywords fields.

    Validates: Requirements 4.4, 4.5, 7.6
    """

    @settings(max_examples=100)
    @given(
        title=title_strategy,
        summary=text_strategy,
        topics=st.lists(text_strategy, min_size=1, max_size=5),
        keywords=st.lists(
            st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=1,
            max_size=10,
        ),
    )
    def test_markdown_contains_all_required_fields(
        self,
        title: str,
        summary: str,
        topics: list[str],
        keywords: list[str],
    ) -> None:
        """Property 8: Generated markdown has all required frontmatter fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"

            episode = create_episode(title=title)
            transcription = create_transcription("Test content")
            analysis = create_analysis(
                summary=summary,
                topics=topics,
                keywords=keywords,
            )

            result_path = generate_markdown(
                episode=episode,
                transcription=transcription,
                analysis=analysis,
                output_path=output_path,
            )

            assert result_path.exists(), "Output file should be created"

            # Parse the frontmatter
            content = result_path.read_text(encoding="utf-8")
            assert content.startswith("---\n"), "Should start with frontmatter"

            parts = content.split("---\n", 2)
            frontmatter = yaml.safe_load(parts[1])

            # Verify all required fields
            assert "title" in frontmatter, "title should be in frontmatter"
            assert "pub_date" in frontmatter, "pub_date should be in frontmatter"
            assert "summary" in frontmatter, "summary should be in frontmatter"
            assert "topics" in frontmatter, "topics should be in frontmatter"
            assert "keywords" in frontmatter, "keywords should be in frontmatter"
            assert "podcast" in frontmatter, "podcast should be in frontmatter"

    def test_markdown_without_analysis_has_basic_fields(self) -> None:
        """Markdown without analysis should still have title and pub_date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"

            episode = create_episode()
            transcription = create_transcription()

            result_path = generate_markdown(
                episode=episode,
                transcription=transcription,
                analysis=None,  # No analysis
                output_path=output_path,
            )

            content = result_path.read_text(encoding="utf-8")
            parts = content.split("---\n", 2)
            frontmatter = yaml.safe_load(parts[1])

            assert "title" in frontmatter
            assert "pub_date" in frontmatter
            # These should NOT be present without analysis
            assert "summary" not in frontmatter
            assert "topics" not in frontmatter


class TestAdvertisementRemovalWithMarkers:
    """
    Property 10: Advertisement Removal with Markers

    For any transcription text with identified advertisement blocks,
    the output text SHALL not contain the advertisement content
    AND SHALL contain "ADVERTISEMENT WAS REMOVED" marker for each removed block.

    Validates: Requirements 6.2, 6.3
    """

    @settings(max_examples=100)
    @given(
        prefix=st.text(min_size=10, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz "),
        ad_content=st.text(min_size=10, max_size=50, alphabet="0123456789ABCDEF"),
        suffix=st.text(min_size=10, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz "),
    )
    def test_ad_content_removed_and_marker_inserted(
        self,
        prefix: str,
        ad_content: str,
        suffix: str,
    ) -> None:
        """Property 10: Ad content removed and marker inserted."""
        # Build text with known ad position
        text = prefix + ad_content + suffix
        ad_start = len(prefix)
        ad_end = ad_start + len(ad_content)
        ad_markers = [(ad_start, ad_end)]

        result = remove_advertisements(text, ad_markers)

        # Ad content should not be in result
        assert ad_content not in result, (
            f"Ad content '{ad_content}' should be removed from result"
        )

        # Marker should be present
        assert AD_REMOVED_MARKER in result, (
            f"Marker should be in result: {result}"
        )

        # Exactly one marker for one ad
        assert count_removed_ads(result) == 1

    @settings(max_examples=100)
    @given(
        num_ads=st.integers(min_value=1, max_value=5),
    )
    def test_multiple_ads_have_multiple_markers(self, num_ads: int) -> None:
        """Multiple ads should result in multiple markers."""
        # Build text with multiple ads
        parts = []
        ad_markers = []
        current_pos = 0

        for i in range(num_ads):
            content = f"content{i} "
            parts.append(content)
            current_pos += len(content)

            ad = f"AD{i}AD"
            ad_start = current_pos
            ad_end = current_pos + len(ad)
            ad_markers.append((ad_start, ad_end))
            parts.append(ad)
            current_pos += len(ad)

        parts.append(" end")
        text = "".join(parts)

        result = remove_advertisements(text, ad_markers)

        # Should have correct number of markers
        assert count_removed_ads(result) == num_ads, (
            f"Expected {num_ads} markers, got {count_removed_ads(result)}"
        )

    def test_no_ads_returns_unchanged_text(self) -> None:
        """Text without ads should be unchanged."""
        text = "This is normal content without any advertisements."

        result = remove_advertisements(text, [])

        assert result == text
        assert AD_REMOVED_MARKER not in result

    def test_overlapping_ads_handled(self) -> None:
        """Overlapping ad markers should be handled gracefully."""
        text = "Start AD CONTENT HERE End"
        # Overlapping markers
        ad_markers = [(6, 17), (10, 21)]

        result = remove_advertisements(text, ad_markers)

        # Should have markers (exact number may vary based on handling)
        assert count_removed_ads(result) >= 1


class TestValidateAdRemoval:
    """Tests for ad removal validation."""

    def test_validate_correct_removal(self) -> None:
        """Validation should pass for correct removal."""
        original = "Start AD_CONTENT End"
        ad_markers = [(6, 16)]
        processed = remove_advertisements(original, ad_markers)

        assert validate_ad_removal(original, processed, ad_markers)

    def test_validate_incorrect_marker_count(self) -> None:
        """Validation should fail with wrong marker count."""
        original = "Start AD_CONTENT End"
        processed = "Start End"  # No marker
        ad_markers = [(6, 16)]

        assert not validate_ad_removal(original, processed, ad_markers)


class TestFormatParagraphs:
    """Tests for paragraph formatting."""

    def test_format_multiple_paragraphs(self) -> None:
        """Multiple paragraphs should be joined with double newlines."""
        paragraphs = ["First paragraph.", "Second paragraph.", "Third paragraph."]

        result = format_paragraphs(paragraphs)

        assert "First paragraph.\n\nSecond paragraph." in result
        assert "Second paragraph.\n\nThird paragraph." in result

    def test_format_empty_paragraphs_filtered(self) -> None:
        """Empty paragraphs should be filtered out."""
        paragraphs = ["First.", "", "  ", "Second."]

        result = format_paragraphs(paragraphs)

        assert result == "First.\n\nSecond."


class TestGenerateFrontmatter:
    """Tests for frontmatter generation."""

    def test_frontmatter_with_analysis(self) -> None:
        """Frontmatter should include analysis data when provided."""
        episode = create_episode()
        analysis = create_analysis()

        frontmatter = generate_frontmatter(episode, analysis)

        assert frontmatter["title"] == episode.title
        assert frontmatter["pub_date"] == "2024-01-15"
        assert frontmatter["podcast"] == episode.podcast_title
        assert frontmatter["summary"] == analysis.summary
        assert frontmatter["topics"] == analysis.topics
        assert frontmatter["keywords"] == analysis.keywords

    def test_frontmatter_without_analysis(self) -> None:
        """Frontmatter without analysis should have basic fields only."""
        episode = create_episode()

        frontmatter = generate_frontmatter(episode, None)

        assert frontmatter["title"] == episode.title
        assert frontmatter["pub_date"] == "2024-01-15"
        assert "summary" not in frontmatter


class TestGenerateOutputFilename:
    """Tests for output filename generation."""

    def test_filename_includes_date_and_title(self) -> None:
        """Filename should include date and sanitized title."""
        episode = EpisodeInfo(
            index=1,
            title="My Great Episode!",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/audio.mp3",
        )

        filename = generate_output_filename(episode)

        assert filename.startswith("20240115_")
        assert filename.endswith(".md")
        assert "!" not in filename  # Special chars removed

    def test_filename_handles_special_characters(self) -> None:
        """Special characters should be sanitized."""
        episode = EpisodeInfo(
            index=1,
            title="Episode: A/B Testing <script>",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/audio.mp3",
        )

        filename = generate_output_filename(episode)

        assert "/" not in filename
        assert ":" not in filename
        assert "<" not in filename
        assert ">" not in filename


class TestValidateMarkdownOutput:
    """Tests for markdown output validation."""

    def test_validate_correct_output(self) -> None:
        """Correct output should pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"

            episode = create_episode()
            transcription = create_transcription()

            generate_markdown(
                episode=episode,
                transcription=transcription,
                analysis=None,
                output_path=output_path,
            )

            assert validate_markdown_output(output_path)

    def test_validate_missing_file(self) -> None:
        """Missing file should fail validation."""
        assert not validate_markdown_output(Path("/nonexistent/file.md"))

    def test_validate_missing_frontmatter(self) -> None:
        """File without frontmatter should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.md"
            output_path.write_text("Just plain text without frontmatter")

            assert not validate_markdown_output(output_path)
