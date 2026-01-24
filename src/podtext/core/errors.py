"""Custom exceptions for podtext."""


class PodtextError(Exception):
    """Base exception for all podtext errors."""

    pass


class ConfigError(PodtextError):
    """Configuration-related errors."""

    pass


class DiscoveryError(PodtextError):
    """Podcast/episode discovery errors."""

    pass


class DownloadError(PodtextError):
    """Media download errors."""

    pass


class TranscriptionError(PodtextError):
    """Transcription errors."""

    pass


class AnalysisError(PodtextError):
    """Claude API errors."""

    pass


class OutputError(PodtextError):
    """File output errors."""

    pass
