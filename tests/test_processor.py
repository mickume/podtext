"""Tests for post-processing.

Feature: podtext
Property 10: Advertisement Removal with Markers
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from podtext.processor import (
    remove_advertisements,
    count_removed_ads,
    format_paragraphs,
    AD_MARKER,
)


class TestRemoveAdvertisements:
    """Tests for advertisement removal."""

    def test_no_ads_returns_original(self):
        """No ad markers returns original text."""
        text = "This is normal content."
        result = remove_advertisements(text, [])
        assert result == text

    def test_single_ad_removed(self):
        """Single ad is removed and marked."""
        text = "Before ad. This is an advertisement. After ad."
        # Mark "This is an advertisement" (positions 11-35)
        result = remove_advertisements(text, [(11, 35)])
        assert AD_MARKER in result
        assert "This is an advertisement" not in result
        assert "Before ad." in result
        assert "After ad." in result

    def test_multiple_ads_removed(self):
        """Multiple ads are removed and marked."""
        text = "Content. AD1. More content. AD2. Final."
        # Mark AD1 (9-13) and AD2 (28-32)
        result = remove_advertisements(text, [(9, 13), (28, 32)])
        assert result.count(AD_MARKER) == 2
        assert "AD1" not in result
        assert "AD2" not in result

    def test_overlapping_ads_handled(self):
        """Overlapping ad markers are handled."""
        text = "A B C D E"
        # Overlapping markers
        result = remove_advertisements(text, [(2, 5), (4, 7)])
        assert AD_MARKER in result

    def test_out_of_bounds_handled(self):
        """Out of bounds markers are handled gracefully."""
        text = "Short"
        result = remove_advertisements(text, [(0, 100)])
        assert result == AD_MARKER

    def test_negative_start_handled(self):
        """Negative start is handled."""
        text = "Hello world"
        result = remove_advertisements(text, [(-5, 5)])
        assert AD_MARKER in result


class TestCountRemovedAds:
    """Tests for counting removed ads."""

    def test_count_no_ads(self):
        """Count returns 0 when no markers."""
        text = "Normal content without markers."
        assert count_removed_ads(text) == 0

    def test_count_single_ad(self):
        """Count returns 1 for single marker."""
        text = f"Before {AD_MARKER} after."
        assert count_removed_ads(text) == 1

    def test_count_multiple_ads(self):
        """Count returns correct number for multiple markers."""
        text = f"{AD_MARKER} text {AD_MARKER} more {AD_MARKER}"
        assert count_removed_ads(text) == 3


class TestFormatParagraphs:
    """Tests for paragraph formatting."""

    def test_single_paragraph(self):
        """Single paragraph returned as-is."""
        paragraphs = ["This is one paragraph."]
        result = format_paragraphs(paragraphs)
        assert result == "This is one paragraph."

    def test_multiple_paragraphs(self):
        """Multiple paragraphs joined with double newlines."""
        paragraphs = ["First paragraph.", "Second paragraph."]
        result = format_paragraphs(paragraphs)
        assert result == "First paragraph.\n\nSecond paragraph."

    def test_empty_paragraphs_filtered(self):
        """Empty paragraphs are filtered out."""
        paragraphs = ["First.", "", "Second.", "   ", "Third."]
        result = format_paragraphs(paragraphs)
        assert result == "First.\n\nSecond.\n\nThird."

    def test_whitespace_trimmed(self):
        """Whitespace is trimmed from paragraphs."""
        paragraphs = ["  Spaced out.  ", "\tTabbed\t"]
        result = format_paragraphs(paragraphs)
        assert result == "Spaced out.\n\nTabbed"


class TestProperty10AdvertisementRemovalWithMarkers:
    """Property 10: Advertisement Removal with Markers.

    For any transcription text with identified advertisement blocks,
    the output text SHALL NOT contain the advertisement content AND
    SHALL contain "ADVERTISEMENT WAS REMOVED" marker for each removed block.

    Validates: Requirements 6.2, 6.3
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        prefix=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"))),
        ad_content=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        suffix=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"))),
    )
    def test_ad_content_removed_marker_inserted(self, prefix, ad_content, suffix):
        """Ad content is removed and marker is inserted."""
        # Construct text with ad content
        text = f"{prefix}{ad_content}{suffix}"
        start = len(prefix)
        end = len(prefix) + len(ad_content)

        result = remove_advertisements(text, [(start, end)])

        # Ad content should not be in result (unless it's also in prefix/suffix)
        if ad_content not in prefix and ad_content not in suffix:
            assert ad_content not in result

        # Marker should be present
        assert AD_MARKER in result

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(num_ads=st.integers(min_value=1, max_value=5))
    def test_marker_count_equals_ad_count(self, num_ads):
        """Number of markers equals number of removed ads."""
        # Create text with multiple ad sections
        parts = []
        markers = []
        position = 0

        for i in range(num_ads):
            content_text = f"Content{i}"
            ad_text = f"AD{i}"

            parts.append(content_text)
            position += len(content_text)

            ad_start = position
            parts.append(ad_text)
            position += len(ad_text)
            ad_end = position

            markers.append((ad_start, ad_end))

        parts.append("Final")
        text = "".join(parts)

        result = remove_advertisements(text, markers)

        # Should have exactly num_ads markers
        assert count_removed_ads(result) == num_ads

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        text=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
    )
    def test_non_ad_content_preserved(self, text):
        """Non-advertisement content is preserved."""
        # Remove a small section from the middle
        if len(text) > 5:
            start = 2
            end = min(5, len(text) - 1)

            before = text[:start]
            after = text[end:]

            result = remove_advertisements(text, [(start, end)])

            # Content before and after ad should be preserved
            assert result.startswith(before)
            assert result.endswith(after)
