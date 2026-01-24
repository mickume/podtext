"""Tests for core data models."""

from datetime import UTC, datetime

from podtext.core.models import (
    AdvertisingBlock,
    Analysis,
    Episode,
    EpisodeOutput,
    Podcast,
    Segment,
    Transcript,
)


class TestPodcast:
    """Tests for Podcast model."""

    def test_create_podcast(self) -> None:
        """Test creating a podcast with all fields."""
        podcast = Podcast(
            title="My Podcast",
            feed_url="https://example.com/feed.xml",
            author="John Doe",
            description="A great podcast",
            artwork_url="https://example.com/art.jpg",
        )
        assert podcast.title == "My Podcast"
        assert podcast.feed_url == "https://example.com/feed.xml"
        assert podcast.author == "John Doe"
        assert podcast.description == "A great podcast"
        assert podcast.artwork_url == "https://example.com/art.jpg"

    def test_create_podcast_minimal(self) -> None:
        """Test creating a podcast with only required fields."""
        podcast = Podcast(
            title="My Podcast",
            feed_url="https://example.com/feed.xml",
        )
        assert podcast.title == "My Podcast"
        assert podcast.author is None
        assert podcast.description is None
        assert podcast.artwork_url is None


class TestEpisode:
    """Tests for Episode model."""

    def test_create_episode(self) -> None:
        """Test creating an episode with all fields."""
        pub_date = datetime(2024, 1, 15, tzinfo=UTC)
        episode = Episode(
            index=1,
            title="Episode 1",
            published=pub_date,
            media_url="https://example.com/ep1.mp3",
            duration=1800,
            description="First episode",
        )
        assert episode.index == 1
        assert episode.title == "Episode 1"
        assert episode.published == pub_date
        assert episode.media_url == "https://example.com/ep1.mp3"
        assert episode.duration == 1800
        assert episode.description == "First episode"

    def test_create_episode_minimal(self) -> None:
        """Test creating an episode with only required fields."""
        episode = Episode(
            index=1,
            title="Episode 1",
            published=datetime.now(UTC),
            media_url="https://example.com/ep1.mp3",
        )
        assert episode.index == 1
        assert episode.duration is None
        assert episode.description is None


class TestSegment:
    """Tests for Segment model."""

    def test_create_segment(self) -> None:
        """Test creating a segment."""
        segment = Segment(
            text="Hello world",
            start=0.0,
            end=2.5,
        )
        assert segment.text == "Hello world"
        assert segment.start == 0.0
        assert segment.end == 2.5


class TestTranscript:
    """Tests for Transcript model."""

    def test_create_transcript(self) -> None:
        """Test creating a transcript."""
        segments = [
            Segment(text="Hello", start=0.0, end=1.0),
            Segment(text="world", start=1.0, end=2.0),
        ]
        transcript = Transcript(
            segments=segments,
            language="en",
            duration=2.0,
        )
        assert len(transcript.segments) == 2
        assert transcript.language == "en"
        assert transcript.duration == 2.0

    def test_full_text_property(self) -> None:
        """Test the full_text property."""
        segments = [
            Segment(text="Hello", start=0.0, end=1.0),
            Segment(text="world", start=1.0, end=2.0),
        ]
        transcript = Transcript(
            segments=segments,
            language="en",
            duration=2.0,
        )
        assert transcript.full_text == "Hello world"

    def test_full_text_empty(self) -> None:
        """Test full_text with no segments."""
        transcript = Transcript(
            segments=[],
            language="en",
            duration=0.0,
        )
        assert transcript.full_text == ""


class TestAdvertisingBlock:
    """Tests for AdvertisingBlock model."""

    def test_create_advertising_block(self) -> None:
        """Test creating an advertising block."""
        block = AdvertisingBlock(
            start_index=5,
            end_index=10,
            confidence=0.95,
        )
        assert block.start_index == 5
        assert block.end_index == 10
        assert block.confidence == 0.95


class TestAnalysis:
    """Tests for Analysis model."""

    def test_create_analysis(self) -> None:
        """Test creating an analysis."""
        analysis = Analysis(
            summary="A great episode.",
            topics=["Topic 1", "Topic 2"],
            keywords=["keyword1", "keyword2"],
            advertising_blocks=[
                AdvertisingBlock(start_index=0, end_index=2, confidence=0.9)
            ],
        )
        assert analysis.summary == "A great episode."
        assert len(analysis.topics) == 2
        assert len(analysis.keywords) == 2
        assert len(analysis.advertising_blocks) == 1

    def test_create_analysis_no_ads(self) -> None:
        """Test creating an analysis without advertising blocks."""
        analysis = Analysis(
            summary="A great episode.",
            topics=["Topic 1"],
            keywords=["keyword1"],
        )
        assert analysis.advertising_blocks == []


class TestEpisodeOutput:
    """Tests for EpisodeOutput model."""

    def test_create_episode_output(
        self,
        sample_episode: Episode,
        sample_transcript: Transcript,
        sample_analysis: Analysis,
    ) -> None:
        """Test creating an episode output."""
        output = EpisodeOutput(
            podcast_title="My Podcast",
            episode=sample_episode,
            transcript=sample_transcript,
            analysis=sample_analysis,
        )
        assert output.podcast_title == "My Podcast"
        assert output.episode == sample_episode
        assert output.transcript == sample_transcript
        assert output.analysis == sample_analysis
