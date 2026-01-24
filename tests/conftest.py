"""Pytest fixtures for podtext tests."""

from datetime import UTC, datetime

import pytest

from podtext.core.models import (
    AdvertisingBlock,
    Analysis,
    Episode,
    EpisodeOutput,
    Podcast,
    Segment,
    Transcript,
)


@pytest.fixture
def sample_podcast() -> Podcast:
    """Create a sample podcast for testing."""
    return Podcast(
        title="Test Podcast",
        feed_url="https://example.com/feed.xml",
        author="Test Author",
        description="A test podcast",
        artwork_url="https://example.com/artwork.jpg",
    )


@pytest.fixture
def sample_episode() -> Episode:
    """Create a sample episode for testing."""
    return Episode(
        index=1,
        title="Test Episode",
        published=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        media_url="https://example.com/episode.mp3",
        duration=3600,
        description="A test episode",
    )


@pytest.fixture
def sample_segments() -> list[Segment]:
    """Create sample transcript segments for testing."""
    return [
        Segment(text="Hello and welcome to the show.", start=0.0, end=2.5),
        Segment(text="Today we're discussing testing.", start=2.5, end=5.0),
        Segment(text="Testing is very important.", start=5.0, end=7.5),
        Segment(text="Let's dive in.", start=7.5, end=9.0),
    ]


@pytest.fixture
def sample_transcript(sample_segments: list[Segment]) -> Transcript:
    """Create a sample transcript for testing."""
    return Transcript(
        segments=sample_segments,
        language="en",
        duration=9.0,
    )


@pytest.fixture
def sample_analysis() -> Analysis:
    """Create a sample analysis for testing."""
    return Analysis(
        summary="This is a test podcast episode about testing.",
        topics=["Software testing basics", "Unit testing best practices"],
        keywords=["testing", "software", "unit tests", "python"],
        advertising_blocks=[],
    )


@pytest.fixture
def sample_analysis_with_ads() -> Analysis:
    """Create a sample analysis with advertising blocks."""
    return Analysis(
        summary="This is a test podcast episode about testing.",
        topics=["Software testing basics", "Unit testing best practices"],
        keywords=["testing", "software", "unit tests", "python"],
        advertising_blocks=[
            AdvertisingBlock(start_index=1, end_index=2, confidence=0.95),
        ],
    )


@pytest.fixture
def sample_output(
    sample_episode: Episode,
    sample_transcript: Transcript,
    sample_analysis: Analysis,
) -> EpisodeOutput:
    """Create a sample episode output for testing."""
    return EpisodeOutput(
        podcast_title="Test Podcast",
        episode=sample_episode,
        transcript=sample_transcript,
        analysis=sample_analysis,
    )


@pytest.fixture
def sample_rss_feed() -> str:
    """Create a sample RSS feed for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Test Podcast</title>
    <description>A test podcast</description>
    <item>
      <title>Episode 1</title>
      <pubDate>Mon, 15 Jan 2024 12:00:00 +0000</pubDate>
      <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" length="1000000"/>
      <itunes:duration>30:00</itunes:duration>
    </item>
    <item>
      <title>Episode 2</title>
      <pubDate>Mon, 08 Jan 2024 12:00:00 +0000</pubDate>
      <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" length="1000000"/>
      <itunes:duration>25:00</itunes:duration>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_itunes_response() -> dict:
    """Create a sample iTunes API response for testing."""
    return {
        "resultCount": 2,
        "results": [
            {
                "collectionName": "Test Podcast",
                "feedUrl": "https://example.com/feed.xml",
                "artistName": "Test Author",
                "artworkUrl600": "https://example.com/artwork.jpg",
            },
            {
                "collectionName": "Another Podcast",
                "feedUrl": "https://example.com/feed2.xml",
                "artistName": "Another Author",
            },
        ],
    }
