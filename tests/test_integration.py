"""Integration tests for Podtext.

Tests end-to-end flow with mocked external APIs, config file creation,
error handling paths, and CLI command execution.

Requirements: 10.4
"""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from podtext.cli.main import cli, format_episode_results, format_search_results
from podtext.core.config import Config, StorageConfig, WhisperConfig, load_config
from podtext.core.pipeline import (
    MediaDownloadError,
    PipelineResult,
    TranscriptionPipelineError,
    run_pipeline,
    run_pipeline_safe,
)
from podtext.services.claude import AnalysisResult
from podtext.services.downloader import DownloadError
from podtext.services.itunes import ITunesAPIError, PodcastSearchResult
from podtext.services.rss import EpisodeInfo, RSSFeedError
from podtext.services.transcriber import TranscriptionError, TranscriptionResult

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Generator[Path]:
    """Create a temporary directory for config files."""
    yield tmp_path


@pytest.fixture
def clean_env() -> Generator[None]:
    """Ensure ANTHROPIC_API_KEY is not set during tests."""
    original = os.environ.pop("ANTHROPIC_API_KEY", None)
    yield
    if original is not None:
        os.environ["ANTHROPIC_API_KEY"] = original


@pytest.fixture
def sample_episode() -> EpisodeInfo:
    """Create a sample episode for testing."""
    return EpisodeInfo(
        index=1,
        title="Test Episode: Integration Testing",
        pub_date=datetime(2024, 1, 15, 10, 30, 0),
        media_url="https://example.com/podcast/episode1.mp3",
    )


@pytest.fixture
def sample_transcription() -> TranscriptionResult:
    """Create a sample transcription result for testing."""
    return TranscriptionResult(
        text="Hello world. This is a test transcription. Welcome to the podcast.",
        paragraphs=[
            "Hello world.",
            "This is a test transcription.",
            "Welcome to the podcast.",
        ],
        language="en",
    )


@pytest.fixture
def sample_analysis() -> AnalysisResult:
    """Create a sample analysis result for testing."""
    return AnalysisResult(
        summary="A test episode about integration testing.",
        topics=["Integration testing basics", "Test automation"],
        keywords=["testing", "integration", "automation"],
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


# ============================================================================
# Full Pipeline Integration Tests
# ============================================================================


class TestFullPipelineIntegration:
    """Integration tests for the full transcription pipeline.

    Tests end-to-end flow with mocked external APIs.

    Validates: Requirement 10.4
    """

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_full_pipeline_success(
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
        """Test successful end-to-end pipeline execution.

        Validates: Requirement 10.4
        """
        # Setup mocks
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = sample_transcription
        mock_analyze.return_value = sample_analysis

        # Execute pipeline
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

        # Verify all stages were called in order
        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()
        mock_analyze.assert_called_once()
        mock_generate.assert_called_once()

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_pipeline_with_podcast_name(
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
        """Test pipeline passes podcast name to output generator."""
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.return_value = sample_transcription
        mock_analyze.return_value = sample_analysis

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            run_pipeline(
                episode=sample_episode,
                config=sample_config,
                podcast_name="Test Podcast",
            )

        # Verify podcast name was passed to generate_markdown
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs.get("podcast_name") == "Test Podcast"

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_pipeline_with_custom_output_path(
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
        """Test pipeline uses custom output path when provided."""
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


# ============================================================================
# Error Handling Integration Tests
# ============================================================================


class TestErrorHandlingIntegration:
    """Integration tests for error handling paths.

    Tests download failures, transcription failures, and graceful degradation.

    Validates: Requirement 10.4
    """

    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_download_failure_raises_error(
        self,
        mock_download: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
    ) -> None:
        """Test that download failure raises MediaDownloadError."""
        mock_download.side_effect = DownloadError("Connection refused")

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
        """Test that transcription failure raises TranscriptionPipelineError."""
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.side_effect = TranscriptionError("Whisper model failed")

        with pytest.raises(TranscriptionPipelineError) as exc_info:
            run_pipeline(episode=sample_episode, config=sample_config)

        assert "transcription failed" in str(exc_info.value).lower()

    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_download_failure_safe_returns_none(
        self,
        mock_download: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
    ) -> None:
        """Test that run_pipeline_safe returns None on download failure."""
        mock_download.side_effect = DownloadError("Network error")

        result = run_pipeline_safe(episode=sample_episode, config=sample_config)

        assert result is None

    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_transcription_failure_safe_returns_none(
        self,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        sample_episode: EpisodeInfo,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that run_pipeline_safe returns None on transcription failure."""
        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.side_effect = TranscriptionError("Audio format not supported")

        result = run_pipeline_safe(episode=sample_episode, config=sample_config)

        assert result is None


# ============================================================================
# Claude API Graceful Degradation Tests
# ============================================================================


class TestClaudeAPIGracefulDegradation:
    """Integration tests for graceful degradation when Claude API is unavailable.

    Validates: Requirement 10.4
    """

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_pipeline_continues_without_api_key(
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
        """Test that pipeline completes without API key, with warning."""
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

        # Pipeline should complete
        assert isinstance(result, PipelineResult)
        # Should have warning about missing API key
        assert any("api key" in w.message.lower() for w in result.warnings)
        # analyze_content should not be called when no API key
        mock_analyze.assert_not_called()

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.core.pipeline.download_with_optional_cleanup")
    def test_pipeline_continues_with_empty_analysis(
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
        """Test that pipeline continues when Claude returns empty analysis."""
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

        # Pipeline should complete
        assert isinstance(result, PipelineResult)
        # Analysis should be empty
        assert result.analysis.summary == ""
        assert result.analysis.topics == []
        assert result.analysis.keywords == []


# ============================================================================
# Config File Creation Tests
# ============================================================================


class TestConfigFileCreation:
    """Integration tests for config file creation on first run.

    Validates: Requirement 10.4
    """

    def test_global_config_auto_created(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that global config is auto-created with defaults on first run."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"

        assert not global_path.exists()

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_global=True,
        )

        # Config should be loaded with defaults
        assert config.whisper.model == "base"
        assert config.storage.temp_storage is False

        # Global config file should be created
        assert global_path.exists()
        content = global_path.read_text()
        assert "[api]" in content
        assert "[storage]" in content
        assert "[whisper]" in content

    def test_existing_config_not_overwritten(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that existing config is not overwritten on load."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        original_content = """
[api]
anthropic_key = "my-custom-key"

[whisper]
model = "large"
"""
        global_path.write_text(original_content)

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_global=True,
        )

        # Config should use existing values
        assert config.api.anthropic_key == "my-custom-key"
        assert config.whisper.model == "large"

        # File content should not be changed
        assert global_path.read_text() == original_content

    def test_local_config_overrides_global(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that local config overrides global config values."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[whisper]
model = "small"

[storage]
temp_storage = false
""")

        local_path.write_text("""
[whisper]
model = "large"
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_global=False,
        )

        # Local should override global
        assert config.whisper.model == "large"
        # Global value should be used for non-overridden keys
        assert config.storage.temp_storage is False


# ============================================================================
# CLI Command Integration Tests
# ============================================================================


class TestCLISearchCommand:
    """Integration tests for the CLI search command.

    Validates: Requirement 10.4
    """

    @patch("podtext.cli.main.search_podcasts")
    def test_search_command_success(self, mock_search: MagicMock, runner: CliRunner) -> None:
        """Test successful search command execution."""
        mock_search.return_value = [
            PodcastSearchResult(
                title="Test Podcast",
                feed_url="https://example.com/feed.xml",
            ),
            PodcastSearchResult(
                title="Another Podcast",
                feed_url="https://example.com/feed2.xml",
            ),
        ]

        result = runner.invoke(cli, ["search", "python", "programming"])

        assert result.exit_code == 0
        assert "Test Podcast" in result.output
        assert "https://example.com/feed.xml" in result.output
        assert "Another Podcast" in result.output

    @patch("podtext.cli.main.search_podcasts")
    def test_search_command_with_limit(self, mock_search: MagicMock, runner: CliRunner) -> None:
        """Test search command with custom limit."""
        mock_search.return_value = []

        result = runner.invoke(cli, ["search", "test", "--limit", "5"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with("test", limit=5)

    @patch("podtext.cli.main.search_podcasts")
    def test_search_command_api_error(self, mock_search: MagicMock, runner: CliRunner) -> None:
        """Test search command handles API errors gracefully."""
        mock_search.side_effect = ITunesAPIError("Connection failed")

        result = runner.invoke(cli, ["search", "test"])

        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()

    @patch("podtext.cli.main.search_podcasts")
    def test_search_command_no_results(self, mock_search: MagicMock, runner: CliRunner) -> None:
        """Test search command with no results."""
        mock_search.return_value = []

        result = runner.invoke(cli, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No podcasts found" in result.output


class TestCLIEpisodesCommand:
    """Integration tests for the CLI episodes command.

    Validates: Requirement 10.4
    """

    @patch("podtext.cli.main.parse_feed")
    def test_episodes_command_success(self, mock_parse: MagicMock, runner: CliRunner) -> None:
        """Test successful episodes command execution."""
        mock_parse.return_value = [
            EpisodeInfo(
                index=1,
                title="Episode 1",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            ),
            EpisodeInfo(
                index=2,
                title="Episode 2",
                pub_date=datetime(2024, 1, 10),
                media_url="https://example.com/ep2.mp3",
            ),
        ]

        result = runner.invoke(cli, ["episodes", "https://example.com/feed.xml"])

        assert result.exit_code == 0
        assert "Episode 1" in result.output
        assert "Episode 2" in result.output
        assert "2024-01-15" in result.output

    @patch("podtext.cli.main.parse_feed")
    def test_episodes_command_with_limit(self, mock_parse: MagicMock, runner: CliRunner) -> None:
        """Test episodes command with custom limit."""
        mock_parse.return_value = []

        result = runner.invoke(cli, ["episodes", "https://example.com/feed.xml", "--limit", "5"])

        assert result.exit_code == 0
        mock_parse.assert_called_once_with("https://example.com/feed.xml", limit=5)

    @patch("podtext.cli.main.parse_feed")
    def test_episodes_command_feed_error(self, mock_parse: MagicMock, runner: CliRunner) -> None:
        """Test episodes command handles feed errors gracefully."""
        mock_parse.side_effect = RSSFeedError("Invalid RSS feed")

        result = runner.invoke(cli, ["episodes", "https://example.com/bad-feed.xml"])

        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()

    @patch("podtext.cli.main.parse_feed")
    def test_episodes_command_no_episodes(self, mock_parse: MagicMock, runner: CliRunner) -> None:
        """Test episodes command with no episodes."""
        mock_parse.return_value = []

        result = runner.invoke(cli, ["episodes", "https://example.com/feed.xml"])

        assert result.exit_code == 0
        assert "No episodes found" in result.output


class TestCLITranscribeCommand:
    """Integration tests for the CLI transcribe command.

    Validates: Requirement 10.4
    """

    @patch("podtext.core.output.generate_markdown")
    @patch("podtext.services.claude.analyze_content")
    @patch("podtext.services.transcriber.transcribe")
    @patch("podtext.services.downloader.download_with_optional_cleanup")
    @patch("podtext.cli.main.parse_feed")
    @patch("podtext.core.config.load_config")
    def test_transcribe_command_success(
        self,
        mock_load_config: MagicMock,
        mock_parse: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        runner: CliRunner,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test successful transcribe command execution."""
        # Setup mocks
        mock_load_config.return_value = sample_config
        mock_parse.return_value = [
            EpisodeInfo(
                index=1,
                title="Test Episode",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            ),
        ]

        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)

        mock_transcribe.return_value = TranscriptionResult(
            text="Test transcription",
            paragraphs=["Test transcription"],
            language="en",
        )
        mock_analyze.return_value = AnalysisResult()

        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml", "1"])

        assert result.exit_code == 0
        assert "Transcribing" in result.output
        mock_transcribe.assert_called_once()
        mock_generate.assert_called_once()

    @patch("podtext.cli.main.parse_feed")
    @patch("podtext.core.config.load_config")
    def test_transcribe_command_episode_not_found(
        self,
        mock_load_config: MagicMock,
        mock_parse: MagicMock,
        runner: CliRunner,
        sample_config: Config,
    ) -> None:
        """Test transcribe command with invalid episode index."""
        mock_load_config.return_value = sample_config
        mock_parse.return_value = [
            EpisodeInfo(
                index=1,
                title="Test Episode",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            ),
        ]

        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml", "99"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("podtext.services.downloader.download_with_optional_cleanup")
    @patch("podtext.cli.main.parse_feed")
    @patch("podtext.core.config.load_config")
    def test_transcribe_command_download_error(
        self,
        mock_load_config: MagicMock,
        mock_parse: MagicMock,
        mock_download: MagicMock,
        runner: CliRunner,
        sample_config: Config,
    ) -> None:
        """Test transcribe command handles download errors gracefully."""
        mock_load_config.return_value = sample_config
        mock_parse.return_value = [
            EpisodeInfo(
                index=1,
                title="Test Episode",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            ),
        ]
        mock_download.side_effect = DownloadError("Connection refused")

        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml", "1"])

        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()

    @patch("podtext.services.transcriber.transcribe")
    @patch("podtext.services.downloader.download_with_optional_cleanup")
    @patch("podtext.cli.main.parse_feed")
    @patch("podtext.core.config.load_config")
    def test_transcribe_command_transcription_error(
        self,
        mock_load_config: MagicMock,
        mock_parse: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        runner: CliRunner,
        sample_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test transcribe command handles transcription errors gracefully."""
        mock_load_config.return_value = sample_config
        mock_parse.return_value = [
            EpisodeInfo(
                index=1,
                title="Test Episode",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            ),
        ]

        media_path = tmp_path / "episode.mp3"
        mock_download.return_value.__enter__ = MagicMock(return_value=media_path)
        mock_download.return_value.__exit__ = MagicMock(return_value=False)
        mock_transcribe.side_effect = TranscriptionError("Whisper failed")

        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml", "1"])

        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()

    @patch("podtext.cli.main.parse_feed")
    @patch("podtext.core.config.load_config")
    def test_transcribe_command_feed_error(
        self,
        mock_load_config: MagicMock,
        mock_parse: MagicMock,
        runner: CliRunner,
        sample_config: Config,
    ) -> None:
        """Test transcribe command handles feed errors gracefully."""
        mock_load_config.return_value = sample_config
        mock_parse.side_effect = RSSFeedError("Invalid feed")

        result = runner.invoke(cli, ["transcribe", "https://example.com/feed.xml", "1"])

        assert result.exit_code == 1
        assert "Error" in result.output or "error" in result.output.lower()


# ============================================================================
# Language Detection Integration Tests
# ============================================================================


class TestLanguageDetectionIntegration:
    """Integration tests for language detection and warnings.

    Validates: Requirement 10.4
    """

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
        """Test that non-English audio results in warning."""
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

        # Should have warning about non-English
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
        """Test that skip_language_check flag is passed to transcriber."""
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


# ============================================================================
# Output Formatting Integration Tests
# ============================================================================


class TestOutputFormattingIntegration:
    """Integration tests for output formatting functions.

    Validates: Requirement 10.4
    """

    def test_format_search_results_complete(self) -> None:
        """Test that search results contain all required fields."""
        results = [
            PodcastSearchResult(
                title="Python Podcast",
                feed_url="https://example.com/python.xml",
            ),
            PodcastSearchResult(
                title="Tech Talk",
                feed_url="https://example.com/tech.xml",
            ),
        ]

        output = format_search_results(results)

        # Verify all titles and URLs are present
        assert "Python Podcast" in output
        assert "https://example.com/python.xml" in output
        assert "Tech Talk" in output
        assert "https://example.com/tech.xml" in output

    def test_format_search_results_empty(self) -> None:
        """Test formatting empty search results."""
        output = format_search_results([])
        assert "No podcasts found" in output

    def test_format_episode_results_complete(self) -> None:
        """Test that episode results contain all required fields."""
        episodes = [
            EpisodeInfo(
                index=1,
                title="Episode One",
                pub_date=datetime(2024, 1, 15),
                media_url="https://example.com/ep1.mp3",
            ),
            EpisodeInfo(
                index=2,
                title="Episode Two",
                pub_date=datetime(2024, 1, 10),
                media_url="https://example.com/ep2.mp3",
            ),
        ]

        output = format_episode_results(episodes)

        # Verify all titles, indices, and dates are present
        assert "1." in output
        assert "Episode One" in output
        assert "2024-01-15" in output
        assert "2." in output
        assert "Episode Two" in output
        assert "2024-01-10" in output

    def test_format_episode_results_empty(self) -> None:
        """Test formatting empty episode results."""
        output = format_episode_results([])
        assert "No episodes found" in output


# ============================================================================
# Environment Variable Integration Tests
# ============================================================================


class TestEnvironmentVariableIntegration:
    """Integration tests for environment variable handling.

    Validates: Requirement 10.4
    """

    def test_env_var_overrides_config_file(self, temp_config_dir: Path) -> None:
        """Test that ANTHROPIC_API_KEY env var overrides config file."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "config-file-key"
""")

        os.environ["ANTHROPIC_API_KEY"] = "env-var-key"
        try:
            config = load_config(
                local_path=local_path,
                global_path=global_path,
                auto_create_global=False,
            )

            # get_anthropic_key should return env var value
            assert config.get_anthropic_key() == "env-var-key"
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_config_file_used_when_env_var_not_set(
        self, temp_config_dir: Path, clean_env: None
    ) -> None:
        """Test that config file value is used when env var is not set."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "config-file-key"
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_global=False,
        )

        assert config.get_anthropic_key() == "config-file-key"


# ============================================================================
# Temporary Storage Integration Tests
# ============================================================================


class TestTemporaryStorageIntegration:
    """Integration tests for temporary storage cleanup.

    Validates: Requirement 10.4
    """

    @patch("podtext.core.pipeline.generate_markdown")
    @patch("podtext.core.pipeline.analyze_content")
    @patch("podtext.core.pipeline.transcribe")
    @patch("podtext.services.downloader.download_media")
    @patch("podtext.services.downloader.cleanup_media_file")
    def test_temp_storage_cleanup_called(
        self,
        mock_cleanup: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        sample_episode: EpisodeInfo,
        sample_transcription: TranscriptionResult,
        sample_analysis: AnalysisResult,
        tmp_path: Path,
    ) -> None:
        """Test that cleanup is called when temp_storage is enabled."""
        config = Config(
            storage=StorageConfig(
                media_dir=str(tmp_path / "media"),
                output_dir=str(tmp_path / "output"),
                temp_storage=True,
            ),
        )

        media_path = tmp_path / "media" / "episode.mp3"
        mock_download.return_value = media_path
        mock_transcribe.return_value = sample_transcription
        mock_analyze.return_value = sample_analysis

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            run_pipeline(
                episode=sample_episode,
                config=config,
            )

        # Cleanup should be called when temp_storage is True
        mock_cleanup.assert_called_once_with(media_path)
