"""Property-based tests for Output Generation.

Feature: podtext
Tests markdown output completeness and advertisement removal with markers.

Validates: Requirements 4.4, 4.5, 6.2, 6.3, 7.6
"""

from __future__ import annotations

from datetime import datetime

import yaml
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from podtext.core.output import generate_markdown_string
from podtext.core.processor import ADVERTISEMENT_MARKER, remove_advertisements
from podtext.services.claude import AnalysisResult
from podtext.services.rss import EpisodeInfo
from podtext.services.transcriber import TranscriptionResult

# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for non-empty text strings (titles, summaries, etc.)
non_empty_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Zs"),
        blacklist_characters="\x00\n\r",
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())

# Strategy for simple text (alphanumeric with spaces)
simple_text_strategy = st.from_regex(
    r"[A-Za-z][A-Za-z0-9 ]{0,50}",
    fullmatch=True,
).filter(lambda s: s.strip())

# Strategy for keywords (simple words)
keyword_strategy = st.from_regex(
    r"[a-z][a-z0-9_-]{0,20}",
    fullmatch=True,
)

# Strategy for topic sentences
topic_strategy = st.from_regex(
    r"[A-Z][A-Za-z0-9 ]{5,50}\.",
    fullmatch=True,
)

# Strategy for valid URLs
url_strategy = st.from_regex(
    r"https://[a-z]{3,10}\.com/[a-z0-9/]{1,20}\.(mp3|m4a|wav)",
    fullmatch=True,
)

# Strategy for datetime objects
datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2030, 12, 31),
)

# Strategy for language codes
language_strategy = st.sampled_from(["en", "es", "fr", "de", "ja", "zh"])


@st.composite
def episode_info_strategy(draw: st.DrawFn) -> EpisodeInfo:
    """Generate a valid EpisodeInfo object."""
    return EpisodeInfo(
        index=draw(st.integers(min_value=1, max_value=1000)),
        title=draw(simple_text_strategy),
        pub_date=draw(datetime_strategy),
        media_url=draw(url_strategy),
    )


@st.composite
def transcription_result_strategy(draw: st.DrawFn) -> TranscriptionResult:
    """Generate a valid TranscriptionResult object."""
    # Generate paragraphs
    num_paragraphs = draw(st.integers(min_value=1, max_value=5))
    paragraphs = [draw(simple_text_strategy) for _ in range(num_paragraphs)]

    # Full text is paragraphs joined
    text = " ".join(paragraphs)

    return TranscriptionResult(
        text=text,
        paragraphs=paragraphs,
        language=draw(language_strategy),
    )


@st.composite
def analysis_result_strategy(draw: st.DrawFn) -> AnalysisResult:
    """Generate a valid AnalysisResult object with non-empty fields."""
    # Generate non-empty summary
    summary = draw(simple_text_strategy)

    # Generate non-empty topics list
    num_topics = draw(st.integers(min_value=1, max_value=5))
    topics = [draw(topic_strategy) for _ in range(num_topics)]

    # Generate non-empty keywords list
    num_keywords = draw(st.integers(min_value=1, max_value=10))
    keywords = [draw(keyword_strategy) for _ in range(num_keywords)]

    return AnalysisResult(
        summary=summary,
        topics=topics,
        keywords=keywords,
        ad_markers=[],  # No ads for basic analysis
    )


@st.composite
def text_with_ad_blocks_strategy(draw: st.DrawFn) -> tuple[str, list[tuple[int, int]]]:
    """Generate text with valid advertisement block positions.

    Returns a tuple of (text, ad_positions) where ad_positions are valid
    non-overlapping ranges within the text.
    """
    # Generate base text parts
    num_parts = draw(st.integers(min_value=2, max_value=5))
    parts = [draw(simple_text_strategy) for _ in range(num_parts)]

    # Generate ad content
    num_ads = draw(st.integers(min_value=1, max_value=min(3, num_parts - 1)))
    ad_contents = [draw(st.from_regex(r"AD[0-9]{1,3}", fullmatch=True)) for _ in range(num_ads)]

    # Interleave parts and ads
    text_parts: list[str] = []
    ad_positions: list[tuple[int, int]] = []
    current_pos = 0

    for i, part in enumerate(parts):
        text_parts.append(part)
        current_pos += len(part)

        # Add ad after this part (but not after the last part)
        if i < len(ad_contents):
            ad_start = current_pos
            ad_content = ad_contents[i]
            text_parts.append(ad_content)
            current_pos += len(ad_content)
            ad_end = current_pos
            ad_positions.append((ad_start, ad_end))

    full_text = "".join(text_parts)
    return full_text, ad_positions


# =============================================================================
# Property 8: Markdown Output Completeness
# =============================================================================


class TestMarkdownOutputCompleteness:
    """Property 8: Markdown Output Completeness

    Feature: podtext, Property 8: Markdown Output Completeness

    For any EpisodeInfo and AnalysisResult, the generated markdown SHALL contain
    valid YAML frontmatter with title, pub_date, summary, topics, and keywords fields.

    **Validates: Requirements 4.4, 4.5, 7.6**
    """

    @settings(max_examples=100)
    @given(
        episode=episode_info_strategy(),
        transcription=transcription_result_strategy(),
        analysis=analysis_result_strategy(),
    )
    def test_markdown_contains_valid_yaml_frontmatter(
        self,
        episode: EpisodeInfo,
        transcription: TranscriptionResult,
        analysis: AnalysisResult,
    ) -> None:
        """Property 8: Markdown Output Completeness

        Feature: podtext, Property 8: Markdown Output Completeness

        For any EpisodeInfo and AnalysisResult, the generated markdown SHALL contain
        valid YAML frontmatter with title, pub_date, summary, topics, and keywords fields.

        **Validates: Requirements 4.4, 4.5, 7.6**
        """
        # Generate markdown
        markdown = generate_markdown_string(episode, transcription, analysis)

        # Property: Markdown SHALL contain valid YAML frontmatter
        assert markdown.startswith("---\n"), (
            "Markdown should start with YAML frontmatter delimiter '---'"
        )

        # Extract frontmatter properly - find the closing --- on its own line
        import re
        match = re.match(r'^---\n(.*?)\n---\n', markdown, re.DOTALL)
        assert match is not None, "Markdown should have opening and closing '---' delimiters"

        yaml_content = match.group(1).strip()

        # Property: Frontmatter SHALL be valid YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise AssertionError(f"Frontmatter is not valid YAML: {e}")

        assert isinstance(data, dict), "Frontmatter should parse to a dictionary"

        # Property: Frontmatter SHALL contain title field
        assert "title" in data, (
            f"Frontmatter should contain 'title' field. Got keys: {list(data.keys())}"
        )
        assert data["title"] == episode.title, (
            f"Title should match episode title. Expected '{episode.title}', got '{data['title']}'"
        )

        # Property: Frontmatter SHALL contain pub_date field
        assert "pub_date" in data, (
            f"Frontmatter should contain 'pub_date' field. Got keys: {list(data.keys())}"
        )
        expected_date = episode.pub_date.strftime("%Y-%m-%d")
        assert data["pub_date"] == expected_date, (
            f"pub_date should match episode date. "
            f"Expected '{expected_date}', got '{data['pub_date']}'"
        )

        # Property: Frontmatter SHALL contain summary field (when analysis has summary)
        assert "summary" in data, (
            f"Frontmatter should contain 'summary' field. Got keys: {list(data.keys())}"
        )
        assert data["summary"] == analysis.summary, "Summary should match analysis summary"

        # Property: Frontmatter SHALL contain topics field (when analysis has topics)
        assert "topics" in data, (
            f"Frontmatter should contain 'topics' field. Got keys: {list(data.keys())}"
        )
        assert isinstance(data["topics"], list), "Topics should be a list"
        assert data["topics"] == analysis.topics, "Topics should match analysis topics"

        # Property: Frontmatter SHALL contain keywords field (when analysis has keywords)
        assert "keywords" in data, (
            f"Frontmatter should contain 'keywords' field. Got keys: {list(data.keys())}"
        )
        assert isinstance(data["keywords"], list), "Keywords should be a list"
        assert data["keywords"] == analysis.keywords, "Keywords should match analysis keywords"

    @settings(max_examples=100)
    @given(
        episode=episode_info_strategy(),
        transcription=transcription_result_strategy(),
        analysis=analysis_result_strategy(),
    )
    def test_markdown_frontmatter_is_parseable_yaml(
        self,
        episode: EpisodeInfo,
        transcription: TranscriptionResult,
        analysis: AnalysisResult,
    ) -> None:
        """Property 8: Markdown Output Completeness - YAML Validity

        Feature: podtext, Property 8: Markdown Output Completeness

        For any generated markdown, the frontmatter SHALL be valid, parseable YAML.

        **Validates: Requirements 4.4, 4.5**
        """
        markdown = generate_markdown_string(episode, transcription, analysis)

        # Extract frontmatter between --- delimiters
        lines = markdown.split("\n")
        yaml_lines: list[str] = []
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

        # Property: YAML SHALL be parseable without errors
        try:
            data = yaml.safe_load(yaml_content)
            assert isinstance(data, dict), "Parsed YAML should be a dictionary"
        except yaml.YAMLError as e:
            raise AssertionError(
                f"Frontmatter YAML is not parseable: {e}\nYAML content:\n{yaml_content}"
            )

    @settings(max_examples=100)
    @given(
        episode=episode_info_strategy(),
        transcription=transcription_result_strategy(),
        analysis=analysis_result_strategy(),
        podcast_name=simple_text_strategy,
    )
    def test_markdown_includes_optional_podcast_name(
        self,
        episode: EpisodeInfo,
        transcription: TranscriptionResult,
        analysis: AnalysisResult,
        podcast_name: str,
    ) -> None:
        """Property 8: Markdown Output Completeness - Optional Fields

        Feature: podtext, Property 8: Markdown Output Completeness

        When podcast_name is provided, the frontmatter SHALL include it.

        **Validates: Requirements 4.5**
        """
        markdown = generate_markdown_string(
            episode, transcription, analysis, podcast_name=podcast_name
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        yaml_content = parts[1].strip()
        data = yaml.safe_load(yaml_content)

        # Property: Podcast name SHALL be included when provided
        assert "podcast" in data, (
            "Frontmatter should contain 'podcast' field when podcast_name is provided"
        )
        assert data["podcast"] == podcast_name, (
            f"Podcast name should match. Expected '{podcast_name}', got '{data['podcast']}'"
        )


# =============================================================================
# Property 10: Advertisement Removal with Markers
# =============================================================================


class TestAdvertisementRemovalWithMarkers:
    """Property 10: Advertisement Removal with Markers

    Feature: podtext, Property 10: Advertisement Removal with Markers

    For any transcription text with identified advertisement blocks, the output text
    SHALL not contain the advertisement content AND SHALL contain "ADVERTISEMENT WAS REMOVED"
    marker for each removed block.

    **Validates: Requirements 6.2, 6.3**
    """

    @settings(max_examples=100)
    @given(
        text_and_ads=text_with_ad_blocks_strategy(),
    )
    def test_advertisement_content_removed_from_output(
        self,
        text_and_ads: tuple[str, list[tuple[int, int]]],
    ) -> None:
        """Property 10: Advertisement Removal with Markers

        Feature: podtext, Property 10: Advertisement Removal with Markers

        For any transcription text with identified advertisement blocks, the output text
        SHALL not contain the advertisement content.

        **Validates: Requirements 6.2**
        """
        text, ad_positions = text_and_ads

        # Skip if no ads
        assume(len(ad_positions) > 0)

        # Extract the actual ad content before removal
        ad_contents = [text[start:end] for start, end in ad_positions]

        # Remove advertisements
        result = remove_advertisements(text, ad_positions)

        # Property: Output text SHALL not contain the advertisement content
        for ad_content in ad_contents:
            assert ad_content not in result, (
                f"Advertisement content '{ad_content}' should NOT be in output.\n"
                f"Original text: '{text}'\n"
                f"Result: '{result}'"
            )

    @settings(max_examples=100)
    @given(
        text_and_ads=text_with_ad_blocks_strategy(),
    )
    def test_marker_inserted_for_each_removed_ad(
        self,
        text_and_ads: tuple[str, list[tuple[int, int]]],
    ) -> None:
        """Property 10: Advertisement Removal with Markers

        Feature: podtext, Property 10: Advertisement Removal with Markers

        For any transcription text with identified advertisement blocks, the output text
        SHALL contain "ADVERTISEMENT WAS REMOVED" marker for each removed block.

        **Validates: Requirements 6.3**
        """
        text, ad_positions = text_and_ads

        # Skip if no ads
        assume(len(ad_positions) > 0)

        # Remove advertisements
        result = remove_advertisements(text, ad_positions)

        # Property: Output SHALL contain marker for each removed block
        marker_count = result.count(f"[{ADVERTISEMENT_MARKER}]")
        expected_count = len(ad_positions)

        assert marker_count == expected_count, (
            f"Expected {expected_count} markers, but found {marker_count}.\n"
            f"Original text: '{text}'\n"
            f"Ad positions: {ad_positions}\n"
            f"Result: '{result}'"
        )

    @settings(max_examples=100)
    @given(
        text_and_ads=text_with_ad_blocks_strategy(),
    )
    def test_non_ad_content_preserved(
        self,
        text_and_ads: tuple[str, list[tuple[int, int]]],
    ) -> None:
        """Property 10: Advertisement Removal with Markers - Content Preservation

        Feature: podtext, Property 10: Advertisement Removal with Markers

        For any transcription text with identified advertisement blocks, the non-ad
        content SHALL be preserved in the output.

        **Validates: Requirements 6.2**
        """
        text, ad_positions = text_and_ads

        # Skip if no ads
        assume(len(ad_positions) > 0)

        # Extract non-ad content segments
        non_ad_segments: list[str] = []
        current_pos = 0

        for ad_start, ad_end in sorted(ad_positions):
            if current_pos < ad_start:
                non_ad_segments.append(text[current_pos:ad_start])
            current_pos = ad_end

        # Add remaining text after last ad
        if current_pos < len(text):
            non_ad_segments.append(text[current_pos:])

        # Remove advertisements
        result = remove_advertisements(text, ad_positions)

        # Property: Non-ad content SHALL be preserved
        for segment in non_ad_segments:
            if segment.strip():  # Only check non-empty segments
                assert segment in result, (
                    f"Non-ad content '{segment}' should be preserved in output.\n"
                    f"Original text: '{text}'\n"
                    f"Result: '{result}'"
                )

    @settings(max_examples=100)
    @given(
        before=simple_text_strategy,
        ad_content=st.from_regex(r"AD[0-9]{1,5}", fullmatch=True),
        after=simple_text_strategy,
    )
    def test_single_ad_removal_and_marker(
        self,
        before: str,
        ad_content: str,
        after: str,
    ) -> None:
        """Property 10: Advertisement Removal with Markers - Single Ad

        Feature: podtext, Property 10: Advertisement Removal with Markers

        For a single advertisement block, the output SHALL not contain the ad content
        AND SHALL contain exactly one marker.

        **Validates: Requirements 6.2, 6.3**
        """
        # Construct text with ad in the middle
        text = f"{before}{ad_content}{after}"
        ad_start = len(before)
        ad_end = ad_start + len(ad_content)
        ad_positions = [(ad_start, ad_end)]

        # Remove advertisement
        result = remove_advertisements(text, ad_positions)

        # Property: Ad content SHALL not be in output
        assert ad_content not in result, f"Ad content '{ad_content}' should not be in result"

        # Property: Exactly one marker SHALL be present
        assert result.count(f"[{ADVERTISEMENT_MARKER}]") == 1, (
            f"Expected exactly 1 marker in result: '{result}'"
        )

        # Property: Non-ad content SHALL be preserved
        assert before in result, f"Content before ad '{before}' should be preserved"
        assert after in result, f"Content after ad '{after}' should be preserved"

    @settings(max_examples=100)
    @given(
        text=simple_text_strategy,
    )
    def test_no_ads_returns_original_text(
        self,
        text: str,
    ) -> None:
        """Property 10: Advertisement Removal with Markers - No Ads

        Feature: podtext, Property 10: Advertisement Removal with Markers

        When there are no advertisement blocks, the output SHALL be the original text
        with no markers.

        **Validates: Requirements 6.2, 6.3**
        """
        # No ad positions
        result = remove_advertisements(text, [])

        # Property: Original text SHALL be returned unchanged
        assert result == text, (
            f"With no ads, text should be unchanged. Expected '{text}', got '{result}'"
        )

        # Property: No markers SHALL be present
        assert ADVERTISEMENT_MARKER not in result, (
            "No markers should be present when no ads removed"
        )

    @settings(max_examples=100)
    @given(
        part1=simple_text_strategy,
        ad1=st.from_regex(r"AD1[0-9]{1,3}", fullmatch=True),
        part2=simple_text_strategy,
        ad2=st.from_regex(r"AD2[0-9]{1,3}", fullmatch=True),
        part3=simple_text_strategy,
    )
    def test_multiple_ads_multiple_markers(
        self,
        part1: str,
        ad1: str,
        part2: str,
        ad2: str,
        part3: str,
    ) -> None:
        """Property 10: Advertisement Removal with Markers - Multiple Ads

        Feature: podtext, Property 10: Advertisement Removal with Markers

        For multiple non-overlapping advertisement blocks, the output SHALL contain
        one marker for each removed block.

        **Validates: Requirements 6.2, 6.3**
        """
        # Construct text with two ads
        text = f"{part1}{ad1}{part2}{ad2}{part3}"

        # Calculate positions
        ad1_start = len(part1)
        ad1_end = ad1_start + len(ad1)
        ad2_start = ad1_end + len(part2)
        ad2_end = ad2_start + len(ad2)

        ad_positions = [(ad1_start, ad1_end), (ad2_start, ad2_end)]

        # Remove advertisements
        result = remove_advertisements(text, ad_positions)

        # Property: Both ad contents SHALL not be in output
        assert ad1 not in result, f"Ad1 '{ad1}' should not be in result"
        assert ad2 not in result, f"Ad2 '{ad2}' should not be in result"

        # Property: Exactly two markers SHALL be present
        marker_count = result.count(f"[{ADVERTISEMENT_MARKER}]")
        assert marker_count == 2, f"Expected 2 markers, got {marker_count}. Result: '{result}'"

        # Property: Non-ad content SHALL be preserved
        assert part1 in result, f"Part1 '{part1}' should be preserved"
        assert part2 in result, f"Part2 '{part2}' should be preserved"
        assert part3 in result, f"Part3 '{part3}' should be preserved"

    @settings(max_examples=100)
    @given(
        episode=episode_info_strategy(),
        transcription=transcription_result_strategy(),
        summary=simple_text_strategy,
    )
    def test_markdown_output_with_ad_markers(
        self,
        episode: EpisodeInfo,
        transcription: TranscriptionResult,
        summary: str,
    ) -> None:
        """Property 10: Advertisement Removal with Markers - Full Pipeline

        Feature: podtext, Property 10: Advertisement Removal with Markers

        When generating markdown with ad markers in AnalysisResult, the output
        SHALL contain the advertisement removal markers.

        **Validates: Requirements 6.2, 6.3**
        """
        # Ensure transcription has enough text for ad markers
        assume(len(transcription.text) > 10)

        # Create ad markers within the text bounds
        text_len = len(transcription.text)
        ad_start = min(5, text_len // 4)
        ad_end = min(ad_start + 5, text_len // 2)

        # Skip if we can't create valid ad markers
        assume(ad_start < ad_end < text_len)

        analysis = AnalysisResult(
            summary=summary,
            topics=["Test topic."],
            keywords=["test"],
            ad_markers=[(ad_start, ad_end)],
        )

        # Generate markdown
        markdown = generate_markdown_string(episode, transcription, analysis)

        # Property: Markdown SHALL contain advertisement marker
        assert ADVERTISEMENT_MARKER in markdown, (
            f"Markdown should contain '{ADVERTISEMENT_MARKER}' when ads are removed.\n"
            f"Markdown:\n{markdown}"
        )
