"""Tests for configuration management.

Feature: podtext
Property tests verify universal properties across generated inputs.
"""

import os
import tempfile
from pathlib import Path

import pytest
import tomli_w
from hypothesis import given, settings, strategies as st

from podtext.config import (
    PodtextConfig,
    ApiConfig,
    StorageConfig,
    WhisperConfig,
    load_config,
    _load_config_file,
    _parse_config_dict,
)


# Strategies for generating config values
api_key_strategy = st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N")))
path_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P")))
model_strategy = st.sampled_from(["tiny", "base", "small", "medium", "large"])


def write_toml_config(path: Path, data: dict) -> None:
    """Helper to write a TOML config file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


class TestConfigLoadingPriority:
    """
    Property 11: Config Loading Priority

    For any configuration key present in both local and global config files,
    the value from the local config file SHALL be used.

    Validates: Requirements 8.1, 8.2
    """

    @settings(max_examples=100)
    @given(
        global_model=model_strategy,
        local_model=model_strategy,
        global_media_dir=path_strategy,
        local_media_dir=path_strategy,
    )
    def test_local_config_takes_precedence_over_global(
        self,
        global_model: str,
        local_model: str,
        global_media_dir: str,
        local_media_dir: str,
    ) -> None:
        """Property 11: Local config values override global config values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            global_path = tmpdir_path / "global" / "config"
            local_path = tmpdir_path / "local" / "config"

            # Write global config
            global_config_data = {
                "api": {"anthropic_key": "global_key"},
                "storage": {
                    "media_dir": global_media_dir,
                    "output_dir": ".podtext/output/",
                    "temp_storage": False,
                },
                "whisper": {"model": global_model},
            }
            write_toml_config(global_path, global_config_data)

            # Write local config with different values
            local_config_data = {
                "api": {"anthropic_key": "local_key"},
                "storage": {
                    "media_dir": local_media_dir,
                    "output_dir": ".podtext/output/",
                    "temp_storage": True,
                },
                "whisper": {"model": local_model},
            }
            write_toml_config(local_path, local_config_data)

            # Load config
            config = load_config(
                local_path=local_path,
                global_path=global_path,
                create_global_if_missing=False,
            )

            # Local values should take precedence
            assert config.whisper.model == local_model, (
                f"Expected local model '{local_model}', got '{config.whisper.model}'"
            )
            assert config.storage.media_dir == local_media_dir, (
                f"Expected local media_dir '{local_media_dir}', got '{config.storage.media_dir}'"
            )
            assert config.api.anthropic_key == "local_key", (
                f"Expected local api key 'local_key', got '{config.api.anthropic_key}'"
            )

    def test_global_config_used_when_no_local(self) -> None:
        """When local config doesn't exist, global config is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            global_path = tmpdir_path / "global" / "config"
            local_path = tmpdir_path / "local" / "config"  # Does not exist

            global_config_data = {
                "api": {"anthropic_key": "global_key"},
                "storage": {
                    "media_dir": "global/downloads/",
                    "output_dir": "global/output/",
                    "temp_storage": True,
                },
                "whisper": {"model": "large"},
            }
            write_toml_config(global_path, global_config_data)

            config = load_config(
                local_path=local_path,
                global_path=global_path,
                create_global_if_missing=False,
            )

            assert config.whisper.model == "large"
            assert config.storage.media_dir == "global/downloads/"
            assert config.api.anthropic_key == "global_key"


class TestEnvironmentVariablePrecedence:
    """
    Property 12: Environment Variable Precedence

    For any ANTHROPIC_API_KEY environment variable value V,
    the Claude API client SHALL use V regardless of config file value.

    Validates: Requirements 8.5
    """

    @settings(max_examples=100)
    @given(
        env_key=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N"))),
        config_key=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_env_var_overrides_config_file(self, env_key: str, config_key: str) -> None:
        """Property 12: Environment variable ANTHROPIC_API_KEY takes precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            global_path = tmpdir_path / "global" / "config"
            local_path = tmpdir_path / "local" / "config"

            # Write config with a key
            config_data = {
                "api": {"anthropic_key": config_key},
                "storage": {
                    "media_dir": ".podtext/downloads/",
                    "output_dir": ".podtext/output/",
                    "temp_storage": False,
                },
                "whisper": {"model": "base"},
            }
            write_toml_config(global_path, config_data)

            # Set environment variable
            original_env = os.environ.get("ANTHROPIC_API_KEY")
            try:
                os.environ["ANTHROPIC_API_KEY"] = env_key

                config = load_config(
                    local_path=local_path,
                    global_path=global_path,
                    create_global_if_missing=False,
                )

                # Environment variable should take precedence
                assert config.api.anthropic_key == env_key, (
                    f"Expected env key '{env_key}', got '{config.api.anthropic_key}'"
                )
            finally:
                # Restore original environment
                if original_env is None:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                else:
                    os.environ["ANTHROPIC_API_KEY"] = original_env

    def test_config_file_used_when_no_env_var(self) -> None:
        """When env var is not set, config file value is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            global_path = tmpdir_path / "global" / "config"
            local_path = tmpdir_path / "local" / "config"

            config_data = {
                "api": {"anthropic_key": "config_api_key"},
                "storage": {
                    "media_dir": ".podtext/downloads/",
                    "output_dir": ".podtext/output/",
                    "temp_storage": False,
                },
                "whisper": {"model": "base"},
            }
            write_toml_config(global_path, config_data)

            # Ensure env var is not set
            original_env = os.environ.get("ANTHROPIC_API_KEY")
            try:
                os.environ.pop("ANTHROPIC_API_KEY", None)

                config = load_config(
                    local_path=local_path,
                    global_path=global_path,
                    create_global_if_missing=False,
                )

                assert config.api.anthropic_key == "config_api_key"
            finally:
                if original_env is not None:
                    os.environ["ANTHROPIC_API_KEY"] = original_env


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_config_values(self) -> None:
        """Default config should have expected values."""
        config = PodtextConfig()

        assert config.api.anthropic_key == ""
        assert config.storage.media_dir == ".podtext/downloads/"
        assert config.storage.output_dir == ".podtext/output/"
        assert config.storage.temp_storage is False
        assert config.whisper.model == "base"

    def test_global_config_created_if_missing(self) -> None:
        """Global config file should be created with defaults if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            global_path = tmpdir_path / "global" / "config"
            local_path = tmpdir_path / "local" / "config"

            assert not global_path.exists()

            # Clear env var to avoid interference
            original_env = os.environ.get("ANTHROPIC_API_KEY")
            try:
                os.environ.pop("ANTHROPIC_API_KEY", None)

                load_config(
                    local_path=local_path,
                    global_path=global_path,
                    create_global_if_missing=True,
                )

                assert global_path.exists(), "Global config should be created"

                # Verify the created config has defaults
                loaded = _load_config_file(global_path)
                assert loaded is not None
                assert loaded.whisper.model == "base"
            finally:
                if original_env is not None:
                    os.environ["ANTHROPIC_API_KEY"] = original_env


class TestConfigParsing:
    """Tests for config file parsing."""

    def test_parse_valid_config_dict(self) -> None:
        """Valid config dictionary should parse correctly."""
        data = {
            "api": {"anthropic_key": "test_key"},
            "storage": {
                "media_dir": "/custom/media/",
                "output_dir": "/custom/output/",
                "temp_storage": True,
            },
            "whisper": {"model": "large"},
        }

        config = _parse_config_dict(data)

        assert config.api.anthropic_key == "test_key"
        assert config.storage.media_dir == "/custom/media/"
        assert config.storage.output_dir == "/custom/output/"
        assert config.storage.temp_storage is True
        assert config.whisper.model == "large"

    def test_parse_partial_config_uses_defaults(self) -> None:
        """Partial config should use defaults for missing values."""
        data = {"whisper": {"model": "small"}}

        config = _parse_config_dict(data)

        assert config.api.anthropic_key == ""  # default
        assert config.storage.media_dir == ".podtext/downloads/"  # default
        assert config.whisper.model == "small"  # from config

    def test_invalid_config_file_returns_none(self) -> None:
        """Invalid/malformed config file should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_path = tmpdir_path / "invalid_config"
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write invalid TOML
            with open(config_path, "w") as f:
                f.write("this is not valid toml [[[")

            result = _load_config_file(config_path)
            assert result is None
