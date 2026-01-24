"""Tests for data models."""

from datetime import datetime

import pytest

from podtext.models.podcast import Episode, Podcast
from podtext.models.transcript import AdSegment, Analysis, Transcript


class TestPodcast:
    """Tests for Podcast model."""

    def test_create_podcast(self):
        """Test creating a Podcast."""
        podcast = Podcast(
            title="Test Podcast",
            feed_url="https://example.com/feed.xml",
            author="Test Author",
        )

        assert podcast.title == "Test Podcast"
        assert podcast.feed_url == "https://example.com/feed.xml"
        assert podcast.author == "Test Author"

    def test_podcast_str_with_author(self):
        """Test string representation with author."""
        podcast = Podcast(
            title="My Podcast",
            feed_url="https://example.com/feed.xml",
            author="John Doe",
        )

        assert str(podcast) == "My Podcast by John Doe"

    def test_podcast_str_without_author(self):
        """Test string representation without author."""
        podcast = Podcast(
            title="My Podcast",
            feed_url="https://example.com/feed.xml",
        )

        assert str(podcast) == "My Podcast"


class TestEpisode:
    """Tests for Episode model."""

    def test_create_episode(self):
        """Test creating an Episode."""
        pub_date = datetime(2024, 1, 15, 10, 30, 0)
        episode = Episode(
            title="Episode 1",
            pub_date=pub_date,
            media_url="https://example.com/ep1.mp3",
            duration=3600,
        )

        assert episode.title == "Episode 1"
        assert episode.pub_date == pub_date
        assert episode.media_url == "https://example.com/ep1.mp3"
        assert episode.duration == 3600

    def test_episode_str(self):
        """Test string representation."""
        episode = Episode(
            title="Great Episode",
            pub_date=datetime(2024, 3, 20),
            media_url="https://example.com/ep.mp3",
        )

        assert str(episode) == "Great Episode (2024-03-20)"

    def test_duration_formatted_hours(self):
        """Test duration formatting with hours."""
        episode = Episode(
            title="Long Episode",
            pub_date=datetime(2024, 1, 1),
            media_url="https://example.com/ep.mp3",
            duration=3661,  # 1:01:01
        )

        assert episode.duration_formatted == "1:01:01"

    def test_duration_formatted_minutes(self):
        """Test duration formatting without hours."""
        episode = Episode(
            title="Short Episode",
            pub_date=datetime(2024, 1, 1),
            media_url="https://example.com/ep.mp3",
            duration=125,  # 2:05
        )

        assert episode.duration_formatted == "2:05"

    def test_duration_formatted_none(self):
        """Test duration formatting when None."""
        episode = Episode(
            title="Episode",
            pub_date=datetime(2024, 1, 1),
            media_url="https://example.com/ep.mp3",
        )

        assert episode.duration_formatted == "Unknown"


class TestTranscript:
    """Tests for Transcript model."""

    def test_create_transcript(self):
        """Test creating a Transcript."""
        transcript = Transcript(
            text="Hello world. This is a test.",
            paragraphs=["Hello world.", "This is a test."],
            language="en",
        )

        assert transcript.text == "Hello world. This is a test."
        assert len(transcript.paragraphs) == 2
        assert transcript.language == "en"

    def test_word_count(self):
        """Test word count calculation."""
        transcript = Transcript(text="one two three four five")
        assert transcript.word_count == 5

    def test_get_text_with_paragraphs(self):
        """Test getting text with paragraph breaks."""
        transcript = Transcript(
            text="First paragraph. Second paragraph.",
            paragraphs=["First paragraph.", "Second paragraph."],
        )

        result = transcript.get_text_with_paragraphs()
        assert result == "First paragraph.\n\nSecond paragraph."

    def test_get_text_with_paragraphs_empty(self):
        """Test getting text when paragraphs empty."""
        transcript = Transcript(text="Just text no paragraphs.")

        result = transcript.get_text_with_paragraphs()
        assert result == "Just text no paragraphs."


class TestAdSegment:
    """Tests for AdSegment model."""

    def test_create_ad_segment(self):
        """Test creating an AdSegment."""
        segment = AdSegment(
            start_text="This episode is sponsored by",
            end_text="now back to the show",
            advertiser="Acme Corp",
            confidence="high",
            start_pos=100,
            end_pos=250,
        )

        assert segment.start_text == "This episode is sponsored by"
        assert segment.end_text == "now back to the show"
        assert segment.advertiser == "Acme Corp"
        assert segment.confidence == "high"
        assert segment.start_pos == 100
        assert segment.end_pos == 250


class TestAnalysis:
    """Tests for Analysis model."""

    def test_create_analysis(self):
        """Test creating an Analysis."""
        analysis = Analysis(
            summary="This is a summary.",
            topics=["Topic 1", "Topic 2"],
            keywords=["key1", "key2", "key3"],
        )

        assert analysis.summary == "This is a summary."
        assert len(analysis.topics) == 2
        assert len(analysis.keywords) == 3

    def test_get_keywords_string(self):
        """Test getting keywords as string."""
        analysis = Analysis(keywords=["ai", "technology", "future"])

        assert analysis.get_keywords_string() == "ai, technology, future"

    def test_get_topics_string(self):
        """Test getting topics as bullet list."""
        analysis = Analysis(topics=["First topic", "Second topic"])

        result = analysis.get_topics_string()
        assert result == "- First topic\n- Second topic"

    def test_empty_analysis(self):
        """Test empty analysis defaults."""
        analysis = Analysis()

        assert analysis.summary == ""
        assert analysis.topics == []
        assert analysis.keywords == []
        assert analysis.ad_segments == []
