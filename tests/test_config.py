"""Unit tests for the Config Manager.

Tests configuration loading, priority handling, and environment variable precedence.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from podtext.core.config import (
    Config,
    ConfigError,
    _deep_merge,
    _dict_to_config,
    _generate_default_config_toml,
    load_config,
)


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


class TestConfigLoading:
    """Tests for basic configuration loading."""

    def test_load_config_with_defaults(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test loading config when no config files exist."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        assert config.api.anthropic_key == ""
        assert config.storage.media_dir == ".podtext/downloads/"
        assert config.storage.output_dir == ".podtext/output/"
        assert config.storage.temp_storage is False
        assert config.whisper.model == "base"

    def test_load_config_from_global(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test loading config from global config file."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "global-key"

[whisper]
model = "small"
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        assert config.api.anthropic_key == "global-key"
        assert config.whisper.model == "small"
        # Defaults should still apply for unspecified values
        assert config.storage.media_dir == ".podtext/downloads/"

    def test_load_config_from_local(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test loading config from local config file."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)

        local_path.write_text("""
[storage]
media_dir = "/custom/media/"
temp_storage = true
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        assert config.storage.media_dir == "/custom/media/"
        assert config.storage.temp_storage is True
        # Defaults should still apply for unspecified values
        assert config.whisper.model == "base"


class TestConfigPriority:
    """Tests for configuration priority (local > global).

    Validates: Requirements 8.1, 8.2
    """

    def test_local_overrides_global(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that local config values override global config values."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "global-key"

[whisper]
model = "small"

[storage]
media_dir = "/global/media/"
""")

        local_path.write_text("""
[whisper]
model = "large"
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        # Local should override global for whisper.model
        assert config.whisper.model == "large"
        # Global values should be used for non-overridden keys
        assert config.api.anthropic_key == "global-key"
        assert config.storage.media_dir == "/global/media/"

    def test_local_partial_override(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that local config can partially override a section."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[storage]
media_dir = "/global/media/"
output_dir = "/global/output/"
temp_storage = false
""")

        local_path.write_text("""
[storage]
media_dir = "/local/media/"
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        # Local should override only media_dir
        assert config.storage.media_dir == "/local/media/"
        # Other storage values should come from global
        assert config.storage.output_dir == "/global/output/"
        assert config.storage.temp_storage is False


class TestEnvironmentVariablePrecedence:
    """Tests for environment variable precedence.

    Validates: Requirements 8.5
    """

    def test_env_var_overrides_config(self, temp_config_dir: Path) -> None:
        """Test that ANTHROPIC_API_KEY env var overrides config file value."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "config-key"
""")

        # Set environment variable
        os.environ["ANTHROPIC_API_KEY"] = "env-key"
        try:
            config = load_config(
                local_path=local_path,
                global_path=global_path,
                auto_create_local=False,
            )

            # get_anthropic_key should return env var value
            assert config.get_anthropic_key() == "env-key"
            # But the config file value should still be stored
            assert config.api.anthropic_key == "config-key"
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_config_used_when_env_var_not_set(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that config file value is used when env var is not set."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "config-key"
""")

        config = load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        assert config.get_anthropic_key() == "config-key"

    def test_empty_env_var_uses_config(self, temp_config_dir: Path) -> None:
        """Test that empty env var falls back to config file value."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "config-key"
""")

        # Set empty environment variable
        os.environ["ANTHROPIC_API_KEY"] = ""
        try:
            config = load_config(
                local_path=local_path,
                global_path=global_path,
                auto_create_local=False,
            )

            # Empty env var should fall back to config
            assert config.get_anthropic_key() == "config-key"
        finally:
            del os.environ["ANTHROPIC_API_KEY"]


class TestAutoCreateLocalConfig:
    """Tests for auto-creating local config.

    Validates: Requirements 8.3
    """

    def test_auto_create_local_config_when_no_config_exists(
        self, temp_config_dir: Path, clean_env: None
    ) -> None:
        """Test that local config is auto-created when no config exists."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"

        assert not local_path.exists()
        assert not global_path.exists()

        load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=True,
        )

        # Local config should be created
        assert local_path.exists()
        # Global config should NOT be created
        assert not global_path.exists()

        content = local_path.read_text()
        assert "[api]" in content
        assert "[storage]" in content
        assert "[whisper]" in content

    def test_no_auto_create_when_disabled(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that local config is not created when auto_create is False."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"

        assert not local_path.exists()
        assert not global_path.exists()

        load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=False,
        )

        assert not local_path.exists()
        assert not global_path.exists()

    def test_no_auto_create_when_global_config_exists(
        self, temp_config_dir: Path, clean_env: None
    ) -> None:
        """Test that local config is not created when global config exists."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        global_path.parent.mkdir(parents=True)

        global_path.write_text("""
[api]
anthropic_key = "global-key"
""")

        load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=True,
        )

        # Local config should NOT be created when global exists
        assert not local_path.exists()
        assert global_path.exists()

    def test_existing_local_config_not_overwritten(
        self, temp_config_dir: Path, clean_env: None
    ) -> None:
        """Test that existing local config is not overwritten."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)

        original_content = """
[api]
anthropic_key = "my-custom-key"
"""
        local_path.write_text(original_content)

        load_config(
            local_path=local_path,
            global_path=global_path,
            auto_create_local=True,
        )

        # Content should not be changed
        assert local_path.read_text() == original_content


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_invalid_whisper_model(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that invalid whisper model raises ConfigError."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)

        local_path.write_text("""
[whisper]
model = "invalid-model"
""")

        with pytest.raises(ConfigError) as exc_info:
            load_config(
                local_path=local_path,
                global_path=global_path,
                auto_create_local=False,
            )

        assert "Invalid whisper model" in str(exc_info.value)
        assert "invalid-model" in str(exc_info.value)

    def test_invalid_toml_syntax(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that invalid TOML syntax raises ConfigError."""
        local_path = temp_config_dir / "local" / "config"
        global_path = temp_config_dir / "global" / "config"
        local_path.parent.mkdir(parents=True)

        local_path.write_text("this is not valid toml [[[")

        with pytest.raises(ConfigError) as exc_info:
            load_config(
                local_path=local_path,
                global_path=global_path,
                auto_create_local=False,
            )

        assert "Invalid TOML" in str(exc_info.value)

    def test_valid_whisper_models(self, temp_config_dir: Path, clean_env: None) -> None:
        """Test that all valid whisper models are accepted."""
        valid_models = ["tiny", "base", "small", "medium", "large"]

        for model in valid_models:
            local_path = temp_config_dir / f"local_{model}" / "config"
            global_path = temp_config_dir / f"global_{model}" / "config"
            local_path.parent.mkdir(parents=True)

            local_path.write_text(f'''
[whisper]
model = "{model}"
''')

            config = load_config(
                local_path=local_path,
                global_path=global_path,
                auto_create_local=False,
            )

            assert config.whisper.model == model


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_deep_merge_simple(self) -> None:
        """Test deep merge with simple dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = _deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self) -> None:
        """Test deep merge with nested dictionaries."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}

        result = _deep_merge(base, override)

        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_deep_merge_does_not_modify_original(self) -> None:
        """Test that deep merge does not modify original dictionaries."""
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}}

        _deep_merge(base, override)

        assert base == {"a": 1, "b": {"c": 2}}
        assert override == {"b": {"d": 3}}

    def test_dict_to_config(self) -> None:
        """Test converting dictionary to Config object."""
        config_dict = {
            "api": {"anthropic_key": "test-key"},
            "storage": {
                "media_dir": "/test/media/",
                "output_dir": "/test/output/",
                "temp_storage": True,
            },
            "whisper": {"model": "large"},
        }

        config = _dict_to_config(config_dict)

        assert config.api.anthropic_key == "test-key"
        assert config.storage.media_dir == "/test/media/"
        assert config.storage.output_dir == "/test/output/"
        assert config.storage.temp_storage is True
        assert config.whisper.model == "large"

    def test_generate_default_config_toml(self) -> None:
        """Test that default config TOML is valid and contains expected sections."""
        toml_content = _generate_default_config_toml()

        assert "[api]" in toml_content
        assert "[storage]" in toml_content
        assert "[whisper]" in toml_content
        assert "anthropic_key" in toml_content
        assert "media_dir" in toml_content
        assert "output_dir" in toml_content
        assert "temp_storage" in toml_content
        assert "model" in toml_content


class TestConfigHelperMethods:
    """Tests for Config helper methods."""

    def test_get_media_dir(self, clean_env: None) -> None:
        """Test get_media_dir returns Path object."""
        config = Config()
        media_dir = config.get_media_dir()

        assert isinstance(media_dir, Path)
        assert str(media_dir) == ".podtext/downloads"

    def test_get_output_dir(self, clean_env: None) -> None:
        """Test get_output_dir returns Path object."""
        config = Config()
        output_dir = config.get_output_dir()

        assert isinstance(output_dir, Path)
        assert str(output_dir) == ".podtext/output"
