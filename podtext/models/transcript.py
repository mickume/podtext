"""Transcript and Analysis data models."""

from dataclasses import dataclass, field


@dataclass
class Transcript:
    """Represents a transcribed episode."""

    text: str
    paragraphs: list[str] = field(default_factory=list)
    language: str = "en"
    segments: list[dict] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        """Return the approximate word count."""
        return len(self.text.split())

    def get_text_with_paragraphs(self) -> str:
        """Return the transcript text with paragraph breaks."""
        if self.paragraphs:
            return "\n\n".join(self.paragraphs)
        return self.text


@dataclass
class AdSegment:
    """Represents a detected advertising segment."""

    start_text: str
    end_text: str
    advertiser: str = ""
    confidence: str = "medium"
    start_pos: int = -1
    end_pos: int = -1


@dataclass
class Analysis:
    """Represents AI analysis of a transcript."""

    summary: str = ""
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    ad_segments: list[AdSegment] = field(default_factory=list)

    def get_keywords_string(self) -> str:
        """Return keywords as comma-separated string."""
        return ", ".join(self.keywords)

    def get_topics_string(self) -> str:
        """Return topics as bullet-point list."""
        return "\n".join(f"- {topic}" for topic in self.topics)
