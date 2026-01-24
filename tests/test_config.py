"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from podtext.config.defaults import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CLEANUP_MEDIA,
    DEFAULT_EPISODE_LIMIT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_WHISPER_MODEL,
    get_default_analysis_md,
    get_default_config,
    get_default_config_toml,
)
from podtext.config.manager import ConfigManager, Config, AnalysisPrompts


class TestDefaults:
    """Tests for default configuration values."""

    def test_get_default_config_structure(self):
        """Test that default config has expected structure."""
        config = get_default_config()

        assert "general" in config
        assert "whisper" in config
        assert "claude" in config
        assert "defaults" in config

    def test_get_default_config_values(self):
        """Test that default config has expected values."""
        config = get_default_config()

        assert config["general"]["output_dir"] == DEFAULT_OUTPUT_DIR
        assert config["general"]["cleanup_media"] == DEFAULT_CLEANUP_MEDIA
        assert config["whisper"]["model"] == DEFAULT_WHISPER_MODEL
        assert config["claude"]["model"] == DEFAULT_CLAUDE_MODEL
        assert config["defaults"]["search_limit"] == DEFAULT_SEARCH_LIMIT
        assert config["defaults"]["episode_limit"] == DEFAULT_EPISODE_LIMIT

    def test_get_default_config_toml_is_valid(self):
        """Test that default TOML content is valid."""
        toml_content = get_default_config_toml()

        assert "[general]" in toml_content
        assert "[whisper]" in toml_content
        assert "[claude]" in toml_content
        assert "[defaults]" in toml_content

    def test_get_default_analysis_md_has_sections(self):
        """Test that default analysis file has required sections."""
        content = get_default_analysis_md()

        assert "## Summary Prompt" in content
        assert "## Topics Prompt" in content
        assert "## Keywords Prompt" in content
        assert "## Advertising Detection Prompt" in content


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_values(self):
        """Test Config default values."""
        config = Config()

        assert config.output_dir == DEFAULT_OUTPUT_DIR
        assert config.cleanup_media == DEFAULT_CLEANUP_MEDIA
        assert config.whisper_model == DEFAULT_WHISPER_MODEL
        assert config.claude_model == DEFAULT_CLAUDE_MODEL
        assert config.search_limit == DEFAULT_SEARCH_LIMIT
        assert config.episode_limit == DEFAULT_EPISODE_LIMIT

    def test_get_api_key_from_config(self):
        """Test getting API key from config."""
        config = Config(claude_api_key="test-key")
        assert config.get_api_key() == "test-key"

    def test_get_api_key_from_env(self, monkeypatch):
        """Test getting API key from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        config = Config()
        assert config.get_api_key() == "env-key"

    def test_config_api_key_takes_precedence(self, monkeypatch):
        """Test that config API key takes precedence over env."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        config = Config(claude_api_key="config-key")
        assert config.get_api_key() == "config-key"

    def test_validate_valid_config(self, monkeypatch):
        """Test validation of valid config."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = Config()
        warnings = config.validate()
        assert len(warnings) == 0

    def test_validate_invalid_whisper_model(self, monkeypatch):
        """Test validation catches invalid whisper model."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = Config(whisper_model="invalid")
        warnings = config.validate()
        assert any("whisper_model" in w for w in warnings)

    def test_validate_missing_api_key(self, monkeypatch):
        """Test validation catches missing API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = Config()
        warnings = config.validate()
        assert any("API key" in w for w in warnings)


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_load_creates_default_config(self, tmp_path, monkeypatch):
        """Test that loading creates default config if none exists."""
        # Use temp home directory
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        manager = ConfigManager(local_dir=tmp_path)
        config = manager.load()

        # Check config was created
        config_file = tmp_path / ".podtext" / "config.toml"
        assert config_file.exists()

        # Check analysis file was created
        analysis_file = tmp_path / ".podtext" / "ANALYSIS.md"
        assert analysis_file.exists()

    def test_load_reads_existing_config(self, tmp_path, monkeypatch):
        """Test loading existing config file."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        # Create config directory and file
        config_dir = tmp_path / ".podtext"
        config_dir.mkdir()

        config_content = """
[general]
output_dir = "./custom"
cleanup_media = false

[whisper]
model = "small"

[claude]
model = "claude-3-opus"
api_key = "custom-key"

[defaults]
search_limit = 20
episode_limit = 15
"""
        (config_dir / "config.toml").write_text(config_content)
        (config_dir / "ANALYSIS.md").write_text(get_default_analysis_md())

        manager = ConfigManager(local_dir=tmp_path)
        config = manager.load()

        assert config.output_dir == "./custom"
        assert config.cleanup_media is False
        assert config.whisper_model == "small"
        assert config.claude_model == "claude-3-opus"
        assert config.claude_api_key == "custom-key"
        assert config.search_limit == 20
        assert config.episode_limit == 15

    def test_local_config_takes_precedence(self, tmp_path, monkeypatch):
        """Test that local config is used over home config."""
        home_dir = tmp_path / "home"
        local_dir = tmp_path / "project"
        home_dir.mkdir()
        local_dir.mkdir()

        monkeypatch.setenv("HOME", str(home_dir))
        monkeypatch.chdir(local_dir)

        # Create home config
        home_config_dir = home_dir / ".podtext"
        home_config_dir.mkdir()
        (home_config_dir / "config.toml").write_text("""
[general]
output_dir = "./home-output"
""")
        (home_config_dir / "ANALYSIS.md").write_text(get_default_analysis_md())

        # Create local config
        local_config_dir = local_dir / ".podtext"
        local_config_dir.mkdir()
        (local_config_dir / "config.toml").write_text("""
[general]
output_dir = "./local-output"
""")
        (local_config_dir / "ANALYSIS.md").write_text(get_default_analysis_md())

        manager = ConfigManager(local_dir=local_dir)
        config = manager.load()

        assert config.output_dir == "./local-output"

    def test_load_prompts_from_analysis_md(self, tmp_path, monkeypatch):
        """Test loading prompts from ANALYSIS.md."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / ".podtext"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text(get_default_config_toml())

        analysis_content = """# Analysis

## Summary Prompt
Generate a summary.

## Topics Prompt
List the topics.

## Keywords Prompt
Extract keywords.

## Advertising Detection Prompt
Find ads.
"""
        (config_dir / "ANALYSIS.md").write_text(analysis_content)

        manager = ConfigManager(local_dir=tmp_path)
        config = manager.load()

        assert "Generate a summary" in config.prompts.summary
        assert "List the topics" in config.prompts.topics
        assert "Extract keywords" in config.prompts.keywords
        assert "Find ads" in config.prompts.advertising

    def test_reload_refreshes_config(self, tmp_path, monkeypatch):
        """Test that reload refreshes config from disk."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        config_dir = tmp_path / ".podtext"
        config_dir.mkdir()
        (config_dir / "ANALYSIS.md").write_text(get_default_analysis_md())

        # Initial config
        (config_dir / "config.toml").write_text("""
[defaults]
search_limit = 5
""")

        manager = ConfigManager(local_dir=tmp_path)
        config1 = manager.load()
        assert config1.search_limit == 5

        # Update config
        (config_dir / "config.toml").write_text("""
[defaults]
search_limit = 25
""")

        config2 = manager.reload()
        assert config2.search_limit == 25
