"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from podtext.core.config import (
    AnalysisConfig,
    Config,
    DefaultsConfig,
    GeneralConfig,
    TranscriptionConfig,
    Verbosity,
    get_api_key,
)
from podtext.core.errors import ConfigError


class TestVerbosity:
    """Tests for Verbosity enum."""

    def test_verbosity_values(self) -> None:
        """Test verbosity enum values."""
        assert Verbosity.QUIET.value == "quiet"
        assert Verbosity.ERROR.value == "error"
        assert Verbosity.NORMAL.value == "normal"
        assert Verbosity.VERBOSE.value == "verbose"


class TestGeneralConfig:
    """Tests for GeneralConfig model."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = GeneralConfig()
        assert config.download_dir == "./downloads"
        assert config.output_dir == "./transcripts"
        assert config.keep_media is False
        assert config.verbosity == Verbosity.NORMAL

    def test_custom_values(self) -> None:
        """Test custom values."""
        config = GeneralConfig(
            download_dir="/custom/downloads",
            output_dir="/custom/output",
            keep_media=True,
            verbosity=Verbosity.VERBOSE,
        )
        assert config.download_dir == "/custom/downloads"
        assert config.keep_media is True
        assert config.verbosity == Verbosity.VERBOSE


class TestTranscriptionConfig:
    """Tests for TranscriptionConfig model."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = TranscriptionConfig()
        assert config.whisper_model == "base"
        assert config.skip_language_check is False


class TestAnalysisConfig:
    """Tests for AnalysisConfig model."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = AnalysisConfig()
        assert config.claude_model == "claude-sonnet-4-20250514"
        assert config.ad_confidence_threshold == 0.9
        assert config.api_key is None

    def test_threshold_validation(self) -> None:
        """Test threshold validation."""
        config = AnalysisConfig(ad_confidence_threshold=0.5)
        assert config.ad_confidence_threshold == 0.5


class TestDefaultsConfig:
    """Tests for DefaultsConfig model."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = DefaultsConfig()
        assert config.search_limit == 10
        assert config.episode_limit == 10


class TestConfig:
    """Tests for Config class."""

    def test_load_defaults(self) -> None:
        """Test loading default configuration."""
        config = Config.load()
        assert config.general.download_dir == "./downloads"
        assert config.transcription.whisper_model == "base"
        assert config.analysis.claude_model == "claude-sonnet-4-20250514"

    def test_load_from_file(self) -> None:
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[general]
download_dir = "/test/downloads"
keep_media = true

[transcription]
whisper_model = "large"

[analysis]
ad_confidence_threshold = 0.8
""")
            f.flush()

            try:
                config = Config.load(f.name)
                assert config.general.download_dir == "/test/downloads"
                assert config.general.keep_media is True
                assert config.transcription.whisper_model == "large"
                assert config.analysis.ad_confidence_threshold == 0.8
            finally:
                os.unlink(f.name)

    def test_default_config_content(self) -> None:
        """Test default config content generation."""
        content = Config._default_config_content()
        assert "[general]" in content
        assert "[transcription]" in content
        assert "[analysis]" in content
        assert "[defaults]" in content
        assert "download_dir" in content

    def test_user_config_path(self) -> None:
        """Test user config path resolution."""
        path = Config._user_config_path()
        assert path == Path.home() / ".podtext" / "config.toml"


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_from_env_var(self) -> None:
        """Test getting API key from environment variable."""
        config = Config()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
        try:
            key = get_api_key(config)
            assert key == "test-key-123"
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_from_config(self) -> None:
        """Test getting API key from config."""
        # Ensure env var is not set
        os.environ.pop("ANTHROPIC_API_KEY", None)

        config = Config()
        config.analysis.api_key = "config-key-456"
        key = get_api_key(config)
        assert key == "config-key-456"

    def test_missing_key_raises_error(self) -> None:
        """Test that missing API key raises ConfigError."""
        # Ensure env var is not set
        os.environ.pop("ANTHROPIC_API_KEY", None)

        config = Config()
        config.analysis.api_key = None

        with pytest.raises(ConfigError) as exc_info:
            get_api_key(config)

        assert "No API key found" in str(exc_info.value)
