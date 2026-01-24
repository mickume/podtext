"""Data models for Podtext."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PodcastSearchResult:
    """Represents a podcast search result from iTunes API."""

    title: str
    feed_url: str


@dataclass
class EpisodeInfo:
    """Represents podcast episode information from RSS feed."""

    index: int
    title: str
    pub_date: datetime
    media_url: str
    podcast_title: str = ""


@dataclass
class TranscriptionResult:
    """Represents the result of audio transcription."""

    text: str
    paragraphs: list[str]
    language: str


@dataclass
class AnalysisResult:
    """Represents Claude AI analysis results."""

    summary: str
    topics: list[str]
    keywords: list[str]
    ad_markers: list[tuple[int, int]] = field(default_factory=list)  # start, end positions
