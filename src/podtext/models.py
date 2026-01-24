"""Data models for Podtext."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PodcastSearchResult:
    """Result from iTunes podcast search."""

    title: str
    feed_url: str


@dataclass
class EpisodeInfo:
    """Information about a podcast episode."""

    index: int
    title: str
    pub_date: datetime
    media_url: str


@dataclass
class TranscriptionResult:
    """Result from audio transcription."""

    text: str
    paragraphs: list[str]
    language: str


@dataclass
class AnalysisResult:
    """Result from Claude content analysis."""

    summary: str
    topics: list[str]
    keywords: list[str]
    ad_markers: list[tuple[int, int]] = field(default_factory=list)
