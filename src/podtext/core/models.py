"""Data models for podtext."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Podcast:
    """Represents a podcast from iTunes search."""

    title: str
    feed_url: str
    author: str | None = None
    description: str | None = None
    artwork_url: str | None = None


@dataclass
class Episode:
    """Represents a podcast episode from RSS feed."""

    index: int
    title: str
    published: datetime
    media_url: str
    duration: int | None = None  # seconds
    description: str | None = None


@dataclass
class Segment:
    """A segment of transcribed text."""

    text: str
    start: float  # seconds
    end: float  # seconds


@dataclass
class Transcript:
    """Complete transcription result."""

    segments: list[Segment]
    language: str
    duration: float

    @property
    def full_text(self) -> str:
        """Return concatenated text from all segments."""
        return " ".join(s.text for s in self.segments)


@dataclass
class AdvertisingBlock:
    """Detected advertising section."""

    start_index: int  # segment index
    end_index: int
    confidence: float


@dataclass
class Analysis:
    """Claude API analysis result."""

    summary: str
    topics: list[str]
    keywords: list[str]
    advertising_blocks: list[AdvertisingBlock] = field(default_factory=list)


@dataclass
class EpisodeOutput:
    """Final output combining all data."""

    podcast_title: str
    episode: Episode
    transcript: Transcript
    analysis: Analysis
