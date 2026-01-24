"""Transcription pipeline for Podtext.

Orchestrates the full transcription flow: download → transcribe → analyze → output.
"""

from pathlib import Path
from typing import Optional

from .config import Config
from .rss import parse_feed, RSSParseError
from .downloader import download_media, cleanup_media, DownloadError
from .transcriber import transcribe, TranscriptionError
from .claude import detect_advertisements, analyze_content
from .processor import remove_advertisements
from .output import generate_markdown, generate_output_filename
from .models import EpisodeInfo, AnalysisResult


class TranscriptionPipelineError(Exception):
    """Error in transcription pipeline."""

    pass


def transcribe_episode(
    feed_url: str,
    index: int,
    config: Config,
    skip_language_check: bool = False,
    output_path: Optional[str] = None,
) -> Path:
    """Transcribe a podcast episode.

    Args:
        feed_url: URL of the podcast RSS feed.
        index: Episode index (1-based).
        config: Application configuration.
        skip_language_check: Skip language detection warning.
        output_path: Optional custom output path.

    Returns:
        Path to the generated markdown file.

    Raises:
        TranscriptionPipelineError: If any stage of the pipeline fails.
    """
    # Step 1: Get episode info from feed
    try:
        episodes = parse_feed(feed_url, limit=index + 10)
    except RSSParseError as e:
        raise TranscriptionPipelineError(f"Failed to parse feed: {e}") from e

    episode = next((ep for ep in episodes if ep.index == index), None)
    if not episode:
        raise TranscriptionPipelineError(f"Episode {index} not found in feed")

    # Step 2: Download media
    try:
        media_path = download_media(episode.media_url, config.media_dir)
    except DownloadError as e:
        raise TranscriptionPipelineError(f"Failed to download media: {e}") from e

    try:
        # Step 3: Transcribe
        try:
            transcription = transcribe(
                media_path,
                model=config.whisper_model,
                skip_language_check=skip_language_check,
            )
        except TranscriptionError as e:
            raise TranscriptionPipelineError(f"Transcription failed: {e}") from e

        # Step 4: Analyze content with Claude
        analysis = AnalysisResult(summary="", topics=[], keywords=[])
        ad_markers: list[tuple[int, int]] = []

        if config.anthropic_key:
            # Detect advertisements
            ad_markers = detect_advertisements(transcription.text, config.anthropic_key)

            # Analyze content
            analysis = analyze_content(transcription.text, config.anthropic_key)
            analysis.ad_markers = ad_markers

        # Step 5: Remove advertisements from text
        if ad_markers:
            processed_text = remove_advertisements(transcription.text, ad_markers)
            # Update transcription text
            transcription.text = processed_text

        # Step 6: Generate output
        if output_path:
            out_path = Path(output_path)
        else:
            filename = generate_output_filename(episode)
            out_path = config.output_dir / filename

        generate_markdown(episode, transcription, analysis, out_path)

        return out_path

    finally:
        # Cleanup media if temp storage is enabled
        if config.temp_storage:
            cleanup_media(media_path)


def get_episode_by_index(feed_url: str, index: int) -> EpisodeInfo:
    """Get a specific episode from a feed by index.

    Args:
        feed_url: URL of the podcast RSS feed.
        index: Episode index (1-based).

    Returns:
        EpisodeInfo for the requested episode.

    Raises:
        TranscriptionPipelineError: If episode is not found.
    """
    try:
        episodes = parse_feed(feed_url, limit=index + 10)
    except RSSParseError as e:
        raise TranscriptionPipelineError(f"Failed to parse feed: {e}") from e

    episode = next((ep for ep in episodes if ep.index == index), None)
    if not episode:
        raise TranscriptionPipelineError(f"Episode {index} not found in feed")

    return episode
