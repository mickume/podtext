"""Service modules for Podtext."""

from podtext.services.downloader import (
    DownloadError,
    cleanup_media_file,
    download_media,
    download_media_to_config_dir,
    download_with_optional_cleanup,
    handle_download_error,
    temporary_download,
)
from podtext.services.itunes import (
    ITunesAPIError,
    PodcastSearchResult,
    search_podcasts,
)
from podtext.services.rss import (
    EpisodeInfo,
    RSSFeedError,
    parse_feed,
)
from podtext.services.transcriber import (
    TranscriptionError,
    TranscriptionResult,
    transcribe,
    transcribe_with_config,
    handle_transcription_error,
)

__all__ = [
    "DownloadError",
    "EpisodeInfo",
    "ITunesAPIError",
    "PodcastSearchResult",
    "RSSFeedError",
    "TranscriptionError",
    "TranscriptionResult",
    "cleanup_media_file",
    "download_media",
    "download_media_to_config_dir",
    "download_with_optional_cleanup",
    "handle_download_error",
    "handle_transcription_error",
    "parse_feed",
    "search_podcasts",
    "temporary_download",
    "transcribe",
    "transcribe_with_config",
]
