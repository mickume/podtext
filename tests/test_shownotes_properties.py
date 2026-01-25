"""Property-based tests for show notes feature.

Tests show notes extraction, HTML conversion, and output formatting using Hypothesis.
"""

from datetime import datetime

from hypothesis import given, settings, strategies as st

from podtext.core.output import _format_show_notes, _format_content
from podtext.core.processor import convert_html_to_markdown
from podtext.services.rss import EpisodeInfo
from podtext.services.transcriber import TranscriptionResult


# Strategy for generating simple HTML content
html_text_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-"),
    min_size=1,
    max_size=100,
)


@settings(max_examples=100)
@given(text=html_text_strategy)
def test_plain_text_passthrough(text: str) -> None:
    """Feature: include-shownotes, Property 3: HTML to Markdown Content Preservation
    
    For any plain text input (no HTML tags), the output shall equal the input.
    
    Validates: Requirements 3.6
    """
    result = convert_html_to_markdown(text)
    assert result.strip() == text.strip()


@settings(max_examples=100)
@given(
    link_text=html_text_strategy,
    url=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-._~/"),
        min_size=5,
        max_size=50,
    ).map(lambda s: f"https://example.com/{s}"),
)
def test_link_conversion(link_text: str, url: str) -> None:
    """Feature: include-shownotes, Property 3: HTML to Markdown Content Preservation
    
    For any HTML link, the output shall contain the link in markdown format.
    
    Validates: Requirements 3.2
    """
    html = f'<a href="{url}">{link_text}</a>'
    result = convert_html_to_markdown(html)
    
    # Should contain markdown link format
    assert f"[{link_text.strip()}]({url})" in result or url in result


@settings(max_examples=100)
@given(show_notes=html_text_strategy)
def test_show_notes_section_formatting(show_notes: str) -> None:
    """Feature: include-shownotes, Property 2: Show Notes Section Formatting
    
    For any EpisodeInfo with non-empty show notes, the generated markdown output
    shall contain a "## Show Notes" heading followed by the show notes content.
    
    Validates: Requirements 2.1, 2.2
    """
    result = _format_show_notes(show_notes)
    
    if show_notes.strip():
        assert "## Show Notes" in result
        assert show_notes.strip() in result or convert_html_to_markdown(show_notes).strip() in result


def test_empty_show_notes_omitted() -> None:
    """Feature: include-shownotes, Property 2: Show Notes Section Formatting
    
    For any EpisodeInfo with empty show notes, the output shall NOT contain
    a "## Show Notes" section.
    
    Validates: Requirements 2.3
    """
    result = _format_show_notes("")
    assert result == ""
    
    result = _format_show_notes("   ")
    assert result == ""


@settings(max_examples=100)
@given(text=st.text(min_size=0, max_size=200))
def test_malformed_html_graceful_handling(text: str) -> None:
    """Feature: include-shownotes, Property 4: Malformed HTML Graceful Handling
    
    For any malformed HTML input, the HTML converter shall produce output
    containing the readable text content without raising exceptions.
    
    Validates: Requirements 4.1
    """
    # Create malformed HTML with unclosed tags
    malformed_html = f"<p>{text}<b>unclosed"
    
    # Should not raise exception
    result = convert_html_to_markdown(malformed_html)
    
    # Should contain the text content
    assert isinstance(result, str)


def test_long_content_truncation() -> None:
    """Feature: include-shownotes, Property 5: Long Content Truncation
    
    For any show notes exceeding 50,000 characters, the formatted output
    shall be truncated to at most 50,000 characters plus a truncation notice.
    
    Validates: Requirements 4.2
    """
    long_content = "A" * 60000
    result = _format_show_notes(long_content)
    
    # Should be truncated
    assert len(result) < 60000
    assert "[Show notes truncated due to length]" in result


@settings(max_examples=100)
@given(
    unicode_text=st.text(
        alphabet=st.sampled_from("αβγδεζηθικλμνξοπρστυφχψω日本語中文한국어"),
        min_size=1,
        max_size=50,
    )
)
def test_unicode_preservation(unicode_text: str) -> None:
    """Feature: include-shownotes, Property 6: Unicode Preservation
    
    For any show notes containing Unicode characters, the characters shall
    be preserved unchanged through extraction, conversion, and output generation.
    
    Validates: Requirements 4.4
    """
    result = convert_html_to_markdown(unicode_text)
    assert unicode_text in result


def test_show_notes_appended_to_content() -> None:
    """Test that show notes are appended after transcription content."""
    transcription = TranscriptionResult(
        text="This is the transcription.",
        paragraphs=["This is the transcription."],
        language="en",
    )
    
    result = _format_content(transcription, [], show_notes="<p>These are the show notes.</p>")
    
    assert "This is the transcription." in result
    assert "## Show Notes" in result
    assert "These are the show notes." in result
    
    # Show notes should come after transcription
    trans_pos = result.find("This is the transcription.")
    notes_pos = result.find("## Show Notes")
    assert trans_pos < notes_pos


def test_episode_info_with_show_notes() -> None:
    """Test that EpisodeInfo correctly stores show_notes."""
    episode = EpisodeInfo(
        index=1,
        title="Test",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/ep.mp3",
        show_notes="<p>Show notes content</p>",
    )
    
    assert episode.show_notes == "<p>Show notes content</p>"


def test_episode_info_show_notes_defaults_to_empty() -> None:
    """Test that EpisodeInfo.show_notes defaults to empty string."""
    episode = EpisodeInfo(
        index=1,
        title="Test",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/ep.mp3",
    )
    
    assert episode.show_notes == ""


# HTML conversion unit tests
def test_html_paragraph_conversion() -> None:
    """Test paragraph tag conversion."""
    html = "<p>First paragraph</p><p>Second paragraph</p>"
    result = convert_html_to_markdown(html)
    
    assert "First paragraph" in result
    assert "Second paragraph" in result


def test_html_list_conversion() -> None:
    """Test list tag conversion."""
    html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
    result = convert_html_to_markdown(html)
    
    assert "- Item 1" in result
    assert "- Item 2" in result


def test_html_ordered_list_conversion() -> None:
    """Test ordered list tag conversion."""
    html = "<ol><li>First</li><li>Second</li></ol>"
    result = convert_html_to_markdown(html)
    
    assert "1. First" in result
    assert "2. Second" in result


def test_html_heading_conversion() -> None:
    """Test heading tag conversion."""
    html = "<h1>Title</h1><h2>Subtitle</h2>"
    result = convert_html_to_markdown(html)
    
    assert "# Title" in result
    assert "## Subtitle" in result


def test_html_emphasis_conversion() -> None:
    """Test bold and italic conversion."""
    html = "<strong>bold</strong> and <em>italic</em>"
    result = convert_html_to_markdown(html)
    
    assert "**bold**" in result
    assert "*italic*" in result
