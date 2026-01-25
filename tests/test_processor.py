"""Unit tests for the processor module.

Tests advertisement removal functionality.

Requirements: 6.2, 6.3
"""

from podtext.core.processor import (
    ADVERTISEMENT_MARKER,
    _normalize_ad_blocks,
    remove_advertisements,
)


class TestNormalizeAdBlocks:
    """Tests for _normalize_ad_blocks helper function."""

    def test_empty_positions(self):
        """Empty ad positions returns empty list."""
        assert _normalize_ad_blocks([], 100) == []

    def test_zero_length_text(self):
        """Zero length text returns empty list."""
        assert _normalize_ad_blocks([(0, 10)], 0) == []

    def test_single_valid_block(self):
        """Single valid block is returned unchanged."""
        result = _normalize_ad_blocks([(5, 15)], 100)
        assert result == [(5, 15)]

    def test_filters_invalid_range(self):
        """Blocks where start >= end are filtered out."""
        result = _normalize_ad_blocks([(10, 5), (5, 15)], 100)
        assert result == [(5, 15)]

    def test_filters_empty_range(self):
        """Blocks where start == end are filtered out."""
        result = _normalize_ad_blocks([(10, 10), (5, 15)], 100)
        assert result == [(5, 15)]

    def test_filters_out_of_bounds_start(self):
        """Blocks starting beyond text length are filtered."""
        result = _normalize_ad_blocks([(100, 110), (5, 15)], 50)
        assert result == [(5, 15)]

    def test_filters_negative_end(self):
        """Blocks ending at or before 0 are filtered."""
        result = _normalize_ad_blocks([(-10, 0), (5, 15)], 100)
        assert result == [(5, 15)]

    def test_clamps_negative_start(self):
        """Negative start is clamped to 0."""
        result = _normalize_ad_blocks([(-5, 10)], 100)
        assert result == [(0, 10)]

    def test_clamps_end_beyond_text(self):
        """End beyond text length is clamped."""
        result = _normalize_ad_blocks([(90, 150)], 100)
        assert result == [(90, 100)]

    def test_sorts_by_start(self):
        """Blocks are sorted by start position."""
        result = _normalize_ad_blocks([(50, 60), (10, 20), (30, 40)], 100)
        assert result == [(10, 20), (30, 40), (50, 60)]

    def test_merges_overlapping(self):
        """Overlapping blocks are merged."""
        result = _normalize_ad_blocks([(10, 30), (20, 40)], 100)
        assert result == [(10, 40)]

    def test_merges_adjacent(self):
        """Adjacent blocks (end == start) are merged."""
        result = _normalize_ad_blocks([(10, 20), (20, 30)], 100)
        assert result == [(10, 30)]

    def test_keeps_separate_non_overlapping(self):
        """Non-overlapping blocks remain separate."""
        result = _normalize_ad_blocks([(10, 20), (30, 40)], 100)
        assert result == [(10, 20), (30, 40)]

    def test_complex_merge_scenario(self):
        """Multiple overlapping blocks merge correctly."""
        # Three overlapping blocks should merge into one
        result = _normalize_ad_blocks([(10, 25), (20, 35), (30, 50)], 100)
        assert result == [(10, 50)]


class TestRemoveAdvertisements:
    """Tests for remove_advertisements function."""

    def test_empty_text(self):
        """Empty text returns empty string."""
        assert remove_advertisements("", [(0, 10)]) == ""

    def test_no_ad_positions(self):
        """No ad positions returns original text."""
        text = "Hello world"
        assert remove_advertisements(text, []) == text

    def test_single_ad_removal(self):
        """Single ad block is removed and marker inserted."""
        text = "Hello this is an ad Goodbye"
        # Remove "this is an ad " (positions 6-20)
        result = remove_advertisements(text, [(6, 20)])
        assert result == f"Hello [{ADVERTISEMENT_MARKER}]Goodbye"
        assert "this is an ad" not in result

    def test_marker_format(self):
        """Marker is inserted in correct format with brackets."""
        text = "Before AD After"
        result = remove_advertisements(text, [(7, 10)])
        assert f"[{ADVERTISEMENT_MARKER}]" in result

    def test_ad_at_start(self):
        """Ad at start of text is handled correctly."""
        text = "AD CONTENT Real content here"
        result = remove_advertisements(text, [(0, 11)])
        assert result == f"[{ADVERTISEMENT_MARKER}]Real content here"

    def test_ad_at_end(self):
        """Ad at end of text is handled correctly."""
        text = "Real content AD CONTENT"
        result = remove_advertisements(text, [(13, 23)])
        assert result == f"Real content [{ADVERTISEMENT_MARKER}]"

    def test_entire_text_is_ad(self):
        """Entire text being an ad returns just the marker."""
        text = "This is all advertisement"
        result = remove_advertisements(text, [(0, len(text))])
        assert result == f"[{ADVERTISEMENT_MARKER}]"

    def test_multiple_ads(self):
        """Multiple separate ads are each replaced with markers."""
        text = "Start AD1 Middle AD2 End"
        result = remove_advertisements(text, [(6, 10), (17, 21)])
        assert result == f"Start [{ADVERTISEMENT_MARKER}]Middle [{ADVERTISEMENT_MARKER}]End"
        assert "AD1" not in result
        assert "AD2" not in result

    def test_overlapping_ads_single_marker(self):
        """Overlapping ads result in single marker."""
        text = "Start OVERLAPPING AD CONTENT End"
        # Two overlapping ranges - merged to (6, 28)
        result = remove_advertisements(text, [(6, 20), (15, 28)])
        # Should have only one marker for merged block
        assert result.count(f"[{ADVERTISEMENT_MARKER}]") == 1
        # The space before "End" is preserved since it's at position 28
        assert result == f"Start [{ADVERTISEMENT_MARKER}] End"

    def test_adjacent_ads_single_marker(self):
        """Adjacent ads result in single marker."""
        text = "Start AD1AD2 End"
        result = remove_advertisements(text, [(6, 9), (9, 12)])
        assert result.count(f"[{ADVERTISEMENT_MARKER}]") == 1
        assert result == f"Start [{ADVERTISEMENT_MARKER}] End"

    def test_preserves_surrounding_whitespace(self):
        """Whitespace around ads is preserved."""
        text = "Hello   AD CONTENT   World"
        result = remove_advertisements(text, [(8, 18)])
        assert result == f"Hello   [{ADVERTISEMENT_MARKER}]   World"

    def test_out_of_bounds_ignored(self):
        """Out of bounds positions are handled gracefully."""
        text = "Short text"
        # Position beyond text length
        result = remove_advertisements(text, [(100, 200)])
        assert result == text

    def test_invalid_range_ignored(self):
        """Invalid ranges (start >= end) are ignored."""
        text = "Hello world"
        result = remove_advertisements(text, [(10, 5)])
        assert result == text

    def test_partial_out_of_bounds_clamped(self):
        """Partially out of bounds positions are clamped."""
        text = "Hello world"
        # End extends beyond text
        result = remove_advertisements(text, [(6, 100)])
        assert result == f"Hello [{ADVERTISEMENT_MARKER}]"
        assert "world" not in result

    def test_content_not_in_result(self):
        """Validates: Requirement 6.2 - Ad content is removed from output."""
        text = "Welcome to the show. BUY OUR PRODUCT NOW! Back to the show."
        ad_content = "BUY OUR PRODUCT NOW! "
        ad_start = text.index(ad_content)
        ad_end = ad_start + len(ad_content)

        result = remove_advertisements(text, [(ad_start, ad_end)])

        # Requirement 6.2: Ad content SHALL be removed
        assert ad_content not in result
        assert "BUY" not in result
        assert "PRODUCT" not in result

    def test_marker_present_for_each_removal(self):
        """Validates: Requirement 6.3 - Marker inserted for each removal."""
        text = "Part1 AD1 Part2 AD2 Part3"

        result = remove_advertisements(text, [(6, 10), (16, 20)])

        # Requirement 6.3: Marker SHALL be inserted where ads removed
        assert result.count(f"[{ADVERTISEMENT_MARKER}]") == 2

    def test_unicode_text(self):
        """Unicode text is handled correctly."""
        text = "Привет AD CONTENT мир"
        result = remove_advertisements(text, [(7, 18)])
        assert result == f"Привет [{ADVERTISEMENT_MARKER}]мир"

    def test_multiline_text(self):
        """Multiline text with ads is handled correctly."""
        text = "Line 1\nAD LINE\nLine 3"
        # "AD LINE" is at positions 7-14, newline at 15
        # To preserve the newline before Line 3, we remove only the ad text
        result = remove_advertisements(text, [(7, 15)])
        # The newline at position 15 is included in the removal
        assert result == f"Line 1\n[{ADVERTISEMENT_MARKER}]Line 3"
