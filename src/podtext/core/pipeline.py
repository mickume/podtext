"""Transcription pipeline for Podtext.

Orchestrates the full transcription flow: download → transcribe → analyze → output.
Handles errors at each stage appropriately with graceful degradation.

Requirements: 3.1, 4.1, 6.1, 7.1
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from podtext.core.config import Config, load_config
from podtext.core.output import generate_markdown
from podtext.core.processor import sanitize_path_component
from podtext.services.claude import (
    AnalysisResult,
    ClaudeAPIError,
    ClaudeAPIUnavailableError,
    analyze_content,
)
from podtext.services.downloader import (
    DownloadError,
    download_with_optional_cleanup,
)
from podtext.services.rss import EpisodeInfo
from podtext.services.transcriber import (
    TranscriptionError,
    TranscriptionResult,
    transcribe,
)


class PipelineError(Exception):
    """Base exception for pipeline errors.

    Raised when a critical error occurs during the pipeline execution
    that prevents completion.
    """


class MediaDownloadError(PipelineError):
    """Raised when media download fails.

    Validates: Requirements 3.4
    """


class TranscriptionPipelineError(PipelineError):
    """Raised when transcription fails.

    Validates: Requirements 4.1
    """


@dataclass
class PipelineWarning:
    """Represents a non-fatal warning during pipeline execution."""

    stage: str
    message: str


@dataclass
class PipelineResult:
    """Result of a successful pipeline execution.

    Attributes:
        output_path: Path to the generated markdown file.
        transcription: The transcription result.
        analysis: The analysis result (may be empty if Claude unavailable).
        warnings: List of non-fatal warnings encountered during execution.
        language_detected: The detected language of the audio.
    """

    output_path: Path
    transcription: TranscriptionResult
    analysis: AnalysisResult
    warnings: list[PipelineWarning] = field(default_factory=list)
    language_detected: str = "unknown"


def _generate_output_path(
    episode: EpisodeInfo,
    podcast_name: str,
    output_dir: Path,
) -> Path:
    """Generate the full output path for a transcribed episode.

    Creates a path in the format: <output_dir>/<podcast_name>/<episode_title>.md

    The podcast name and episode title are sanitized to be safe for file systems
    and limited to 30 characters each.

    Args:
        episode: Episode information from RSS feed.
        podcast_name: Name of the podcast.
        output_dir: Base output directory from config.

    Returns:
        Full path for the output markdown file.

    Validates: Requirements 1.1, 4.1, 4.2, 4.4
    """
    # Sanitize podcast name, use fallback if empty
    safe_podcast = sanitize_path_component(
        podcast_name,
        max_length=30,
        fallback="unknown-podcast",
    )

    # Sanitize episode title, use fallback with index if empty
    safe_title = sanitize_path_component(
        episode.title,
        max_length=30,
        fallback=f"episode_{episode.index}",
    )

    return output_dir / safe_podcast / f"{safe_title}.md"


def _display_warning(message: str) -> None:
    """Display a warning message to stderr.

    Args:
        message: Warning message to display.
    """
    print(f"Warning: {message}", file=sys.stderr)


def _display_error(message: str) -> None:
    """Display an error message to stderr.

    Args:
        message: Error message to display.
    """
    print(f"Error: {message}", file=sys.stderr)


def run_pipeline(
    episode: EpisodeInfo,
    config: Config | None = None,
    skip_language_check: bool = False,
    podcast_name: str = "",
    output_path: Path | None = None,
) -> PipelineResult:
    """Run the full transcription pipeline for an episode.

    Orchestrates the complete flow:
    1. Download media file from episode URL
    2. Transcribe audio using MLX-Whisper
    3. Analyze content using Claude API (with graceful degradation)
    4. Generate markdown output with frontmatter

    Error handling:
    - Media download failure: Raises MediaDownloadError
    - Transcription failure: Raises TranscriptionPipelineError
    - Non-English audio: Displays warning, continues transcription
    - Claude API unavailable: Displays warning, outputs transcript without AI analysis

    Args:
        episode: Episode information from RSS feed.
        config: Application configuration. If None, loads from default paths.
        skip_language_check: If True, bypass language detection.
        podcast_name: Optional podcast name for frontmatter.
        output_path: Optional custom output path. If None, uses config output_dir.

    Returns:
        PipelineResult with output path, transcription, analysis, and warnings.

    Raises:
        MediaDownloadError: If media download fails.
        TranscriptionPipelineError: If transcription fails.

    Validates: Requirements 3.1, 4.1, 6.1, 7.1
    """
    # Load configuration if not provided
    if config is None:
        config = load_config()

    warnings: list[PipelineWarning] = []

    # Stage 1: Download media file
    # Uses context manager for optional cleanup based on config.storage.temp_storage
    try:
        with download_with_optional_cleanup(
            url=episode.media_url,
            config=config,
        ) as media_path:
            # Stage 2: Transcribe audio
            try:
                transcription = transcribe(
                    audio_path=media_path,
                    model=config.whisper.model,
                    skip_language_check=skip_language_check,
                )
            except TranscriptionError as e:
                raise TranscriptionPipelineError(f"Transcription failed: {e}") from e

            # Check for non-English content (warning already displayed by transcriber)
            language_detected = transcription.language
            if not skip_language_check and language_detected not in ("en", "unknown"):
                warnings.append(
                    PipelineWarning(
                        stage="transcription",
                        message=f"Detected language '{language_detected}' is not English",
                    )
                )

            # Stage 3: Analyze content with Claude API
            # Graceful degradation if API unavailable
            api_key = config.get_anthropic_key()

            if api_key:
                try:
                    analysis = analyze_content(
                        text=transcription.text,
                        api_key=api_key,
                        warn_on_unavailable=True,
                    )

                    # Check if analysis is empty (API was unavailable)
                    if not analysis.summary and not analysis.topics and not analysis.keywords:
                        warnings.append(
                            PipelineWarning(
                                stage="analysis",
                                message="Claude API returned empty analysis",
                            )
                        )

                except ClaudeAPIUnavailableError as e:
                    _display_warning(
                        f"Claude API unavailable: {e}. "
                        "Transcript will be output without AI analysis."
                    )
                    warnings.append(
                        PipelineWarning(
                            stage="analysis",
                            message=f"Claude API unavailable: {e}",
                        )
                    )
                    analysis = AnalysisResult()

                except ClaudeAPIError as e:
                    _display_warning(
                        f"Claude API error: {e}. Transcript will be output without AI analysis."
                    )
                    warnings.append(
                        PipelineWarning(
                            stage="analysis",
                            message=f"Claude API error: {e}",
                        )
                    )
                    analysis = AnalysisResult()
            else:
                _display_warning(
                    "Anthropic API key not configured. "
                    "Transcript will be output without AI analysis."
                )
                warnings.append(
                    PipelineWarning(
                        stage="analysis",
                        message="Anthropic API key not configured",
                    )
                )
                analysis = AnalysisResult()

            # Stage 4: Generate markdown output
            if output_path is None:
                output_path = _generate_output_path(
                    episode=episode,
                    podcast_name=podcast_name,
                    output_dir=config.get_output_dir(),
                )

            generate_markdown(
                episode=episode,
                transcription=transcription,
                analysis=analysis,
                output_path=output_path,
                podcast_name=podcast_name,
            )

            return PipelineResult(
                output_path=output_path,
                transcription=transcription,
                analysis=analysis,
                warnings=warnings,
                language_detected=language_detected,
            )

    except DownloadError as e:
        raise MediaDownloadError(f"Media download failed: {e}") from e


def run_pipeline_safe(
    episode: EpisodeInfo,
    config: Config | None = None,
    skip_language_check: bool = False,
    podcast_name: str = "",
    output_path: Path | None = None,
) -> PipelineResult | None:
    """Run the pipeline with error handling and user-friendly messages.

    Same as run_pipeline() but catches exceptions and displays
    user-friendly error messages instead of raising.

    Args:
        episode: Episode information from RSS feed.
        config: Application configuration. If None, loads from default paths.
        skip_language_check: If True, bypass language detection.
        podcast_name: Optional podcast name for frontmatter.
        output_path: Optional custom output path.

    Returns:
        PipelineResult on success, None on failure.

    Validates: Requirements 3.4, 4.1, 6.4
    """
    try:
        return run_pipeline(
            episode=episode,
            config=config,
            skip_language_check=skip_language_check,
            podcast_name=podcast_name,
            output_path=output_path,
        )
    except MediaDownloadError as e:
        _display_error(str(e))
        return None
    except TranscriptionPipelineError as e:
        _display_error(str(e))
        return None
    except Exception as e:
        _display_error(f"Unexpected error: {e}")
        return None


class TranscriptionPipeline:
    """Class-based interface for the transcription pipeline.

    Provides a reusable pipeline instance with configuration.
    Useful for processing multiple episodes with the same settings.

    Example:
        >>> config = load_config()
        >>> pipeline = TranscriptionPipeline(config)
        >>> result = pipeline.process(episode)
        >>> print(f"Output: {result.output_path}")
    """

    def __init__(
        self,
        config: Config | None = None,
        skip_language_check: bool = False,
        podcast_name: str = "",
    ) -> None:
        """Initialize the pipeline with configuration.

        Args:
            config: Application configuration. If None, loads from default paths.
            skip_language_check: Default setting for language check bypass.
            podcast_name: Default podcast name for frontmatter.
        """
        self.config = config if config is not None else load_config()
        self.skip_language_check = skip_language_check
        self.podcast_name = podcast_name

    def process(
        self,
        episode: EpisodeInfo,
        output_path: Path | None = None,
        skip_language_check: bool | None = None,
        podcast_name: str | None = None,
    ) -> PipelineResult:
        """Process an episode through the pipeline.

        Args:
            episode: Episode information from RSS feed.
            output_path: Optional custom output path.
            skip_language_check: Override default language check setting.
            podcast_name: Override default podcast name.

        Returns:
            PipelineResult with output path and metadata.

        Raises:
            MediaDownloadError: If media download fails.
            TranscriptionPipelineError: If transcription fails.
        """
        return run_pipeline(
            episode=episode,
            config=self.config,
            skip_language_check=(
                skip_language_check if skip_language_check is not None else self.skip_language_check
            ),
            podcast_name=podcast_name if podcast_name is not None else self.podcast_name,
            output_path=output_path,
        )

    def process_safe(
        self,
        episode: EpisodeInfo,
        output_path: Path | None = None,
        skip_language_check: bool | None = None,
        podcast_name: str | None = None,
    ) -> PipelineResult | None:
        """Process an episode with error handling.

        Same as process() but returns None on failure instead of raising.

        Args:
            episode: Episode information from RSS feed.
            output_path: Optional custom output path.
            skip_language_check: Override default language check setting.
            podcast_name: Override default podcast name.

        Returns:
            PipelineResult on success, None on failure.
        """
        return run_pipeline_safe(
            episode=episode,
            config=self.config,
            skip_language_check=(
                skip_language_check if skip_language_check is not None else self.skip_language_check
            ),
            podcast_name=podcast_name if podcast_name is not None else self.podcast_name,
            output_path=output_path,
        )
