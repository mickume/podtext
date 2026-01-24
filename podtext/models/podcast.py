"""Podcast and Episode data models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Podcast:
    """Represents a podcast from search results."""

    title: str
    feed_url: str
    author: str = ""
    artwork_url: str = ""
    genre: str = ""

    def __str__(self) -> str:
        """Return a formatted string representation."""
        if self.author:
            return f"{self.title} by {self.author}"
        return self.title


@dataclass
class Episode:
    """Represents a podcast episode."""

    title: str
    pub_date: datetime
    media_url: str
    duration: int | None = None
    description: str = ""
    guid: str = ""
    language: str = ""

    def __str__(self) -> str:
        """Return a formatted string representation."""
        date_str = self.pub_date.strftime("%Y-%m-%d")
        return f"{self.title} ({date_str})"

    @property
    def duration_formatted(self) -> str:
        """Return duration as HH:MM:SS string."""
        if self.duration is None:
            return "Unknown"

        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:d}:{seconds:02d}"
