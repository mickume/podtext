"""Transcription pipeline orchestration."""

import warnings
from pathlib import Path

from podtext.claude import analyze_with_fallback
from podtext.config import PodtextConfig, get_anthropic_api_key
from podtext.downloader import DownloadError, cleanup_media_file, download_media
from podtext.models import AnalysisResult, EpisodeInfo, TranscriptionResult
from podtext.output import generate_markdown, generate_output_filename
from podtext.rss import RSSParseError, get_episode_by_index, parse_feed
from podtext.transcriber import TranscriptionError, transcribe


class PipelineError(Exception):
    """Exception raised when the transcription pipeline fails."""

    pass


async def run_transcription_pipeline(
    feed_url: str,
    episode_index: int,
    config: PodtextConfig,
    skip_language_check: bool = False,
    output_path: Path | None = None,
) -> Path:
    """
    Run the complete transcription pipeline.

    Steps:
    1. Fetch episode info from RSS feed
    2. Download media file
    3. Transcribe using MLX-Whisper
    4. Analyze with Claude AI (if available)
    5. Generate markdown output
    6. Cleanup temp files (if configured)

    Args:
        feed_url: URL of the podcast RSS feed
        episode_index: Index of the episode to transcribe
        config: Application configuration
        skip_language_check: Skip language detection warning
        output_path: Optional custom output path

    Returns:
        Path to the generated markdown file

    Raises:
        PipelineError: If any step of the pipeline fails
    """
    media_path: Path | None = None

    try:
        # Step 1: Get episode info
        episodes = await parse_feed(feed_url, limit=max(episode_index, 10))
        episode = get_episode_by_index(episodes, episode_index)

        if episode is None:
            raise PipelineError(f"Episode {episode_index} not found in feed")

        # Step 2: Download media
        media_dir = Path(config.storage.media_dir)
        media_path = await download_media(
            url=episode.media_url,
            dest_dir=media_dir,
        )

        # Step 3: Transcribe
        transcription = transcribe(
            audio_path=media_path,
            model=config.whisper.model,
            skip_language_check=skip_language_check,
        )

        # Step 4: Analyze with Claude (if API key available)
        api_key = get_anthropic_api_key(config)
        analysis = analyze_with_fallback(transcription.text, api_key)

        # Step 5: Generate output
        if output_path is None:
            output_dir = Path(config.storage.output_dir)
            filename = generate_output_filename(episode)
            output_path = output_dir / filename

        result_path = generate_markdown(
            episode=episode,
            transcription=transcription,
            analysis=analysis,
            output_path=output_path,
        )

        return result_path

    except RSSParseError as e:
        raise PipelineError(f"Failed to parse RSS feed: {e}") from e
    except DownloadError as e:
        raise PipelineError(f"Failed to download media: {e}") from e
    except TranscriptionError as e:
        raise PipelineError(f"Transcription failed: {e}") from e
    except Exception as e:
        raise PipelineError(f"Pipeline failed: {e}") from e
    finally:
        # Step 6: Cleanup temp files if configured
        if config.storage.temp_storage and media_path is not None:
            cleanup_media_file(media_path)


async def transcribe_episode(
    episode: EpisodeInfo,
    config: PodtextConfig,
    skip_language_check: bool = False,
    output_path: Path | None = None,
) -> Path:
    """
    Transcribe a single episode (when episode info is already known).

    Args:
        episode: Episode information
        config: Application configuration
        skip_language_check: Skip language detection warning
        output_path: Optional custom output path

    Returns:
        Path to the generated markdown file
    """
    media_path: Path | None = None

    try:
        # Download media
        media_dir = Path(config.storage.media_dir)
        media_path = await download_media(
            url=episode.media_url,
            dest_dir=media_dir,
        )

        # Transcribe
        transcription = transcribe(
            audio_path=media_path,
            model=config.whisper.model,
            skip_language_check=skip_language_check,
        )

        # Analyze with Claude
        api_key = get_anthropic_api_key(config)
        analysis = analyze_with_fallback(transcription.text, api_key)

        # Generate output
        if output_path is None:
            output_dir = Path(config.storage.output_dir)
            filename = generate_output_filename(episode)
            output_path = output_dir / filename

        return generate_markdown(
            episode=episode,
            transcription=transcription,
            analysis=analysis,
            output_path=output_path,
        )

    finally:
        if config.storage.temp_storage and media_path is not None:
            cleanup_media_file(media_path)
