"""Unit tests for the transcription pipeline.

Tests the full transcription flow: download → transcribe → analyze → output.

Requirements: 3.1, 4.1, 6.1, 7.1
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podtext.core.config import Config, StorageConfig, WhisperConfig
from podtext.core.pipeline import (
    MediaDownloadError,
    PipelineResult,
    PipelineWarning,
    TranscriptionPipeline,
    TranscriptionPipelineError,
    _generate_output_path,
    run_pipeline,
    run_pipeline_safe,
)
from podtext.services.claude import AnalysisResult
from podtext.services.downloader import DownloadError
from podtext.services.rss import EpisodeInfo
from podtext.services.transcriber import TranscriptionError, TranscriptionResult


@pytest.fixture
def sample_episode() -> EpisodeInfo:
    """Create a sample episode for testing."""
    return EpisodeInfo(
        index=1,
        title="Test Episode: A Great Podcast",
        pub_date=datetime(2024, 1, 15, 10, 30, 0),
        media_url="https://example.com/podcast/episode1.mp3",
    )


@pytest.fixture
def sample_transcription() -> TranscriptionResult:
    """Create a sample transcription result for testing."""
    return TranscriptionResult(
        text="Hello world. This is a test transcription.",
        paragraphs=["Hello world.", "This is a test transcription."],
        language="en",
    )


@pytest.fixture
def sample_analysis() -> AnalysisResult:
    """Create a sample analysis result for testing."""
    return AnalysisResult(
        summary="A test episode about podcasting.",
        topics=["Podcasting basics", "Audio quality"],
        keywords=["podcast", "audio", "test"],
        ad_markers=[],
    )


@pytest.fixture
def sample_config(tmp_path: Path) -> Config:
    """Create a sample configuration for testing."""
    return Config(
        storage=StorageConfig(
            media_dir=str(tmp_path / "media"),
            output_dir=str(tmp_path / "output"),
            temp_storage=True,
        ),
        whisper=WhisperConfig(model="base"),
    )


class TestGenerateOutputPath:
    """Tests for _generate_output_path function."""

    def test_generates_path_with_podcast_subdirectory(
        self, sample_episode: EpisodeInfo, tmp_path: Path
    ) -> None:
        """Test that path includes podcast subdirectory."""
        path = _generate_output_path(sample_episode, "My Podcast", tmp_path)
        assert path.parent.name == "My Podcast"
        assert path.suffix == ".md"

    def test_sanitizes_special_characters(self, tmp_path: Path) -> None:
        """Test that special characters are sanitized."""
        episode = EpisodeInfo(
            index=1,
            title="Episode: Test/With\\Special*Characters?",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/ep.mp3",
        )
        path = _generate_output_path(episode, "Podcast/Name:Test", tmp_path)

        # Check podcast directory name is sanitized
        assert "/" not in path.parent.name
        assert "\\" not in path.parent.name
        assert ":" not in path.parent.name

        # Check filename is sanitized
        assert "/" not in path.name
        assert "\\" not in path.name
        assert "*" not in path.name
        assert "?" not in path.name

    def test_truncates_long_names(self, tmp_path: Path) -> None:
        """Test that very long names are truncated to 30 chars."""
        episode = EpisodeInfo(
            index=1,
            title="A" * 200,  # Very long title
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/ep.mp3",
        )
        path = _generate_output_path(episode, "B" * 200, tmp_path)

        # Podcast directory name should be max 30 chars
        assert len(path.parent.name) <= 30
        # Filename (without .md) should be max 30 chars
        assert len(path.stem) <= 30

    def test_handles_empty_podcast_name(self, sample_episode: EpisodeInfo, tmp_path: Path) -> None:
        """Test fallback for empty podcast name."""
        path = _generate_output_path(sample_episode, "", tmp_path)
        assert path.parent.name == "unknown-podcast"

    def test_handles_empty_episode_title(self, tmp_path: Path) -> None:
        """Test fallback for empty episode title."""
        episode = EpisodeInfo(
            index=5,
            title="",
            pub_date=datetime(2024, 1, 15),
            media_url="https://example.com/ep.mp3",
        )
        path = _generate_output_path(episode, "My Podcast", tmp_path)
        assert path.stem == "episode_5"

    def test_custom_output_path_overrides(
        self, sample_episode: EpisodeInfo, tmp_path: Path
    ) -> None:
        """Test that custom output_path in run_pipeline overrides generated path."""
        # This is tested in TestRunPipeline.test_custom_output_path
        pass


class TestRunPipeline:
    """Tests for run_pipeline function.

    Validates: Requirements 3.1, 4.1, 6.1, 7.1
    """

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_successful_pipeline_execution(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_transcription: TranscriptionResult,
        sample_analysis: AnalysisResult,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test successful execution of the full pipeline.

        Validates: Requirements 3.1, 4.1, 6.1, 7.1
        """
        # Setup mocks
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = sample_transcription
        mock_analyze.return_value = sample_analysis

        # Set API key in config
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = run_pipeline(
                episode=sample_episode,
                config=sample_config,
            )

        # Verify result
        assert isinstance(result, PipelineResult)
        assert result.transcription == sample_transcription
        assert result.analysis == sample_analysis
        assert result.language_detected == "en"
        assert result.output_path.suffix == ".md"

        # Verify all stages were called
        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()
        mock_analyze.assert_called_once()
        mock_generate.assert_called_once()

    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_download_failure_raises_error(
        self,
        mock_download: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
    ) -> None:
        """Test that download failure raises MediaDownloadError.

        Validates: Requirement 3.4
        """
        mock_download.side_effect = DownloadError("Connection failed")

        with pytest.raises(MediaDownloadError) as exc_info:
            run_pipeline(episode=sample_episode, config=sample_config)

        assert "download failed" in str(exc_info.value).lower()

    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_transcription_failure_raises_error(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that transcription failure raises TranscriptionPipelineError.

        Validates: Requirement 4.1
        """
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.side_effect = TranscriptionError("Whisper failed")

        with pytest.raises(TranscriptionPipelineError) as exc_info:
            run_pipeline(episode=sample_episode, config=sample_config)

        assert "transcription failed" in str(exc_info.value).lower()

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_claude_unavailable_continues_with_warning(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_transcription: TranscriptionResult,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that Claude API unavailability results in warning, not failure.

        Validates: Requirement 6.4
        """
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = sample_transcription
        # Return empty analysis (simulating API unavailable)
        mock_analyze.return_value = AnalysisResult()

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = run_pipeline(
                episode=sample_episode,
                config=sample_config,
            )

        # Pipeline should complete successfully
        assert isinstance(result, PipelineResult)
        # Analysis should be empty
        assert result.analysis.summary == ""
        # Should have a warning about empty analysis
        assert any("analysis" in w.stage for w in result.warnings)

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_no_api_key_continues_with_warning(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_transcription: TranscriptionResult,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that missing API key results in warning, not failure.

        Validates: Requirement 6.4
        """
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = sample_transcription

        # Clear API key
        with patch.dict("os.environ", {}, clear=True):
            result = run_pipeline(
                episode=sample_episode,
                config=sample_config,
            )

        # Pipeline should complete successfully
        assert isinstance(result, PipelineResult)
        # Should have a warning about missing API key
        assert any("api key" in w.message.lower() for w in result.warnings)

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_non_english_language_warning(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_analysis: AnalysisResult,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that non-English audio results in warning.

        Validates: Requirement 5.2
        """
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        # Return transcription with non-English language
        mock_transcribe.return_value = TranscriptionResult(
            text="Bonjour le monde.",
            paragraphs=["Bonjour le monde."],
            language="fr",
        )
        mock_analyze.return_value = sample_analysis

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = run_pipeline(
                episode=sample_episode,
                config=sample_config,
            )

        # Should have a warning about non-English
        assert result.language_detected == "fr"
        assert any("not english" in w.message.lower() for w in result.warnings)

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_skip_language_check_flag(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_analysis: AnalysisResult,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that skip_language_check flag is passed to transcriber.

        Validates: Requirement 5.3
        """
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = TranscriptionResult(
            text="Test",
            paragraphs=["Test"],
            language="unknown",
        )
        mock_analyze.return_value = sample_analysis

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            run_pipeline(
                episode=sample_episode,
                config=sample_config,
                skip_language_check=True,
            )

        # Verify skip_language_check was passed
        mock_transcribe.assert_called_once()
        call_kwargs = mock_transcribe.call_args[1]
        assert call_kwargs.get("skip_language_check") is True

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_custom_output_path(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_transcription: TranscriptionResult,
        sample_analysis: AnalysisResult,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that custom output path is used."""
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = sample_transcription
        mock_analyze.return_value = sample_analysis

        custom_output = tmp_path / "custom" / "output.md"

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = run_pipeline(
                episode=sample_episode,
                config=sample_config,
                output_path=custom_output,
            )

        assert result.output_path == custom_output


class TestRunPipelineSafe:
    """Tests for run_pipeline_safe function."""

    @patch("podtext.core.pipeline.run_pipeline")
    def test_returns_result_on_success(
        self,
        mock_run: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that successful execution returns result."""
        expected_result = PipelineResult(
            output_path=tmp_path / "output.md",
            transcription=TranscriptionResult(text="Test", paragraphs=[], language="en"),
            analysis=AnalysisResult(),
        )
        mock_run.return_value = expected_result

        result = run_pipeline_safe(episode=sample_episode, config=sample_config)

        assert result == expected_result

    @patch("podtext.core.pipeline.run_pipeline")
    def test_returns_none_on_download_error(
        self,
        mock_run: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
    ) -> None:
        """Test that download error returns None."""
        mock_run.side_effect = MediaDownloadError("Download failed")

        result = run_pipeline_safe(episode=sample_episode, config=sample_config)

        assert result is None

    @patch("podtext.core.pipeline.run_pipeline")
    def test_returns_none_on_transcription_error(
        self,
        mock_run: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
    ) -> None:
        """Test that transcription error returns None."""
        mock_run.side_effect = TranscriptionPipelineError("Transcription failed")

        result = run_pipeline_safe(episode=sample_episode, config=sample_config)

        assert result is None


class TestTranscriptionPipelineClass:
    """Tests for TranscriptionPipeline class."""

    @patch("podtext.core.pipeline.run_pipeline")
    def test_process_calls_run_pipeline(
        self,
        mock_run: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that process() calls run_pipeline with correct args."""
        expected_result = PipelineResult(
            output_path=tmp_path / "output.md",
            transcription=TranscriptionResult(text="Test", paragraphs=[], language="en"),
            analysis=AnalysisResult(),
        )
        mock_run.return_value = expected_result

        pipeline = TranscriptionPipeline(
            config=sample_config,
            skip_language_check=True,
            podcast_name="Test Podcast",
        )
        result = pipeline.process(sample_episode)

        assert result == expected_result
        mock_run.assert_called_once_with(
            episode=sample_episode,
            config=sample_config,
            skip_language_check=True,
            podcast_name="Test Podcast",
            output_path=None,
        )

    @patch("podtext.core.pipeline.run_pipeline")
    def test_process_allows_overrides(
        self,
        mock_run: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that process() allows overriding default settings."""
        expected_result = PipelineResult(
            output_path=tmp_path / "output.md",
            transcription=TranscriptionResult(text="Test", paragraphs=[], language="en"),
            analysis=AnalysisResult(),
        )
        mock_run.return_value = expected_result

        pipeline = TranscriptionPipeline(
            config=sample_config,
            skip_language_check=False,
            podcast_name="Default Podcast",
        )
        custom_output = tmp_path / "custom.md"
        pipeline.process(
            sample_episode,
            skip_language_check=True,
            podcast_name="Override Podcast",
            output_path=custom_output,
        )

        mock_run.assert_called_once_with(
            episode=sample_episode,
            config=sample_config,
            skip_language_check=True,
            podcast_name="Override Podcast",
            output_path=custom_output,
        )

    @patch("podtext.core.pipeline.run_pipeline_safe")
    def test_process_safe_returns_none_on_error(
        self,
        mock_run: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
    ) -> None:
        """Test that process_safe() returns None on error."""
        mock_run.return_value = None

        pipeline = TranscriptionPipeline(config=sample_config)
        result = pipeline.process_safe(sample_episode)

        assert result is None


class TestPipelineWarning:
    """Tests for PipelineWarning dataclass."""

    def test_warning_creation(self) -> None:
        """Test creating a pipeline warning."""
        warning = PipelineWarning(
            stage="analysis",
            message="Claude API unavailable",
        )
        assert warning.stage == "analysis"
        assert warning.message == "Claude API unavailable"
