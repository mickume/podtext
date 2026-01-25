"""Property-based tests for enhanced metadata feature.

Tests feed_url and media_url inclusion in frontmatter using Hypothesis.
"""

from datetime import datetime

import yaml
from hypothesis import given, settings, strategies as st

from podtext.core.output import _format_frontmatter
from podtext.services.claude import AnalysisResult
from podtext.services.rss import EpisodeInfo


# Strategy for generating valid URLs
url_strategy = st.text(
    alphabet=st.sampled_from(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~:/?#[]@!$&'()*+,;="
    ),
    min_size=10,
    max_size=200,
).map(lambda s: f"https://example.com/{s}")


@settings(max_examples=100)
@given(
    feed_url=url_strategy,
    media_url=url_strategy,
)
def test_feed_url_round_trip(feed_url: str, media_url: str) -> None:
    """Feature: enhanced-metadata, Property 1: Feed URL Round-Trip
    
    For any EpisodeInfo with a non-None feed_url, generating frontmatter
    and parsing the resulting YAML should yield the same feed_url value.
    
    Validates: Requirements 1.1, 1.3
    """
    episode = EpisodeInfo(
        index=1,
        title="Test Episode",
        pub_date=datetime(2024, 1, 15),
        media_url=media_url,
        feed_url=feed_url,
    )
    analysis = AnalysisResult()
    
    frontmatter = _format_frontmatter(episode, analysis)
    
    # Parse the YAML content (strip the --- delimiters)
    yaml_content = frontmatter.strip().strip("-").strip()
    parsed = yaml.safe_load(yaml_content)
    
    assert parsed["feed_url"] == feed_url


@settings(max_examples=100)
@given(media_url=url_strategy)
def test_media_url_round_trip(media_url: str) -> None:
    """Feature: enhanced-metadata, Property 2: Media URL Round-Trip
    
    For any EpisodeInfo with a media_url, generating frontmatter and
    parsing the resulting YAML should yield the same media_url value.
    
    Validates: Requirements 2.1, 2.2
    """
    episode = EpisodeInfo(
        index=1,
        title="Test Episode",
        pub_date=datetime(2024, 1, 15),
        media_url=media_url,
    )
    analysis = AnalysisResult()
    
    frontmatter = _format_frontmatter(episode, analysis)
    
    # Parse the YAML content
    yaml_content = frontmatter.strip().strip("-").strip()
    parsed = yaml.safe_load(yaml_content)
    
    assert parsed["media_url"] == media_url


@settings(max_examples=100)
@given(
    title=st.text(alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"), min_size=1, max_size=100),
    podcast_name=st.text(alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"), min_size=0, max_size=50),
    summary=st.text(alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.!?,"), min_size=0, max_size=200),
    topics=st.lists(st.text(alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"), min_size=1, max_size=50), max_size=5),
    keywords=st.lists(st.text(alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_"), min_size=1, max_size=20), max_size=10),
)
def test_existing_fields_preserved(
    title: str,
    podcast_name: str,
    summary: str,
    topics: list[str],
    keywords: list[str],
) -> None:
    """Feature: enhanced-metadata, Property 3: Existing Fields Preserved
    
    For any valid EpisodeInfo and AnalysisResult, the generated frontmatter
    should contain all existing fields (title, pub_date) and conditionally
    include podcast, summary, topics, and keywords when provided.
    
    Validates: Requirements 3.1, 3.2
    """
    episode = EpisodeInfo(
        index=1,
        title=title,
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/ep.mp3",
        feed_url="https://example.com/feed.xml",
    )
    analysis = AnalysisResult(
        summary=summary,
        topics=topics,
        keywords=keywords,
        ad_markers=[],
    )
    
    frontmatter = _format_frontmatter(episode, analysis, podcast_name)
    
    # Parse the YAML content
    yaml_content = frontmatter.strip().strip("-").strip()
    parsed = yaml.safe_load(yaml_content)
    
    # Required fields always present
    assert "title" in parsed
    assert "pub_date" in parsed
    assert "media_url" in parsed
    
    # Conditional fields
    if podcast_name:
        assert parsed.get("podcast") == podcast_name
    
    if summary:
        assert parsed.get("summary") == summary
    
    if topics:
        assert parsed.get("topics") == topics
    
    if keywords:
        assert parsed.get("keywords") == keywords


def test_feed_url_omitted_when_none() -> None:
    """Test that feed_url is omitted from frontmatter when None."""
    episode = EpisodeInfo(
        index=1,
        title="Test Episode",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/ep.mp3",
        feed_url=None,
    )
    analysis = AnalysisResult()
    
    frontmatter = _format_frontmatter(episode, analysis)
    
    # Parse the YAML content
    yaml_content = frontmatter.strip().strip("-").strip()
    parsed = yaml.safe_load(yaml_content)
    
    assert "feed_url" not in parsed
    assert "media_url" in parsed  # media_url should always be present


def test_media_url_always_present() -> None:
    """Test that media_url is always present in frontmatter."""
    episode = EpisodeInfo(
        index=1,
        title="Test Episode",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/episode.mp3",
    )
    analysis = AnalysisResult()
    
    frontmatter = _format_frontmatter(episode, analysis)
    
    yaml_content = frontmatter.strip().strip("-").strip()
    parsed = yaml.safe_load(yaml_content)
    
    assert "media_url" in parsed
    assert parsed["media_url"] == "https://example.com/episode.mp3"


def test_episode_info_with_feed_url() -> None:
    """Test that EpisodeInfo correctly stores feed_url."""
    episode = EpisodeInfo(
        index=1,
        title="Test",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/ep.mp3",
        feed_url="https://example.com/feed.xml",
    )
    
    assert episode.feed_url == "https://example.com/feed.xml"


def test_episode_info_feed_url_defaults_to_none() -> None:
    """Test that EpisodeInfo.feed_url defaults to None."""
    episode = EpisodeInfo(
        index=1,
        title="Test",
        pub_date=datetime(2024, 1, 15),
        media_url="https://example.com/ep.mp3",
    )
    
    assert episode.feed_url is None
