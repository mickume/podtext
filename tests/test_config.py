"""Tests for configuration management.

Feature: podtext
Property 11: Config Loading Priority
Property 12: Environment Variable Precedence
"""

import os
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path

from podtext.config import (
    Config,
    load_config,
    get_global_config_path,
    get_local_config_path,
    _parse_config_file,
    _merge_configs,
    DEFAULT_CONFIG,
)


# Strategy for generating valid config values
config_values = st.fixed_dictionaries({
    "anthropic_key": st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    "media_dir": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "P"))).map(lambda x: x.replace("\x00", "a")),
    "output_dir": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "P"))).map(lambda x: x.replace("\x00", "a")),
    "temp_storage": st.booleans(),
    "whisper_model": st.sampled_from(["tiny", "base", "small", "medium", "large"]),
})


def create_config_file(path: Path, api_key: str = "", media_dir: str = ".podtext/downloads/",
                       output_dir: str = ".podtext/output/", temp_storage: bool = False,
                       whisper_model: str = "base") -> None:
    """Create a TOML config file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""\
[api]
anthropic_key = "{api_key}"

[storage]
media_dir = "{media_dir}"
output_dir = "{output_dir}"
temp_storage = {str(temp_storage).lower()}

[whisper]
model = "{whisper_model}"
"""
    path.write_text(content)


class TestConfigBasics:
    """Basic configuration tests."""

    def test_default_config_values(self):
        """Test that Config has correct defaults."""
        config = Config()
        assert config.anthropic_key == ""
        assert config.media_dir == Path(".podtext/downloads/")
        assert config.output_dir == Path(".podtext/output/")
        assert config.temp_storage is False
        assert config.whisper_model == "base"

    def test_global_config_created_if_missing(self, mock_home):
        """Test that global config is created with defaults if missing."""
        global_path = mock_home / ".podtext" / "config"
        assert not global_path.exists()

        load_config(create_global=True)

        assert global_path.exists()
        assert DEFAULT_CONFIG in global_path.read_text()

    def test_global_config_not_created_when_disabled(self, mock_home):
        """Test that global config is not created when create_global=False."""
        global_path = mock_home / ".podtext" / "config"
        assert not global_path.exists()

        load_config(create_global=False)

        assert not global_path.exists()

    def test_parse_nonexistent_file(self, temp_dir):
        """Test parsing a file that doesn't exist returns empty dict."""
        result = _parse_config_file(temp_dir / "nonexistent")
        assert result == {}

    def test_parse_invalid_toml(self, temp_dir):
        """Test parsing invalid TOML returns empty dict."""
        bad_file = temp_dir / "bad.toml"
        bad_file.write_text("this is not valid [toml")
        result = _parse_config_file(bad_file)
        assert result == {}


class TestConfigMerging:
    """Test configuration merging logic."""

    def test_merge_empty_configs(self):
        """Merging empty configs produces empty config."""
        result = _merge_configs({}, {})
        assert result == {}

    def test_merge_override_wins(self):
        """Override values take precedence."""
        base = {"key": "base_value"}
        override = {"key": "override_value"}
        result = _merge_configs(base, override)
        assert result["key"] == "override_value"

    def test_merge_nested_dicts(self):
        """Nested dicts are merged recursively."""
        base = {"api": {"key1": "value1", "key2": "value2"}}
        override = {"api": {"key2": "new_value2"}}
        result = _merge_configs(base, override)
        assert result["api"]["key1"] == "value1"
        assert result["api"]["key2"] == "new_value2"


class TestProperty11ConfigLoadingPriority:
    """Property 11: Config Loading Priority.

    For any configuration key present in both local and global config files,
    the value from the local config file SHALL be used.

    Validates: Requirements 8.1, 8.2
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        global_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))),
        local_key=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_local_config_overrides_global(self, mock_home, temp_dir, monkeypatch, global_key, local_key, clean_env):
        """Local config values override global config values."""
        # Change working directory to temp_dir for local config
        monkeypatch.chdir(temp_dir)

        # Create global config with global_key
        global_path = mock_home / ".podtext" / "config"
        create_config_file(global_path, api_key=global_key)

        # Create local config with local_key
        local_path = temp_dir / ".podtext" / "config"
        create_config_file(local_path, api_key=local_key)

        # Load config
        config = load_config(create_global=False)

        # Local should override global
        assert config.anthropic_key == local_key

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        global_model=st.sampled_from(["tiny", "small", "medium"]),
        local_model=st.sampled_from(["base", "large"]),
    )
    def test_local_whisper_model_overrides_global(self, mock_home, temp_dir, monkeypatch, global_model, local_model, clean_env):
        """Local whisper model config overrides global."""
        monkeypatch.chdir(temp_dir)

        global_path = mock_home / ".podtext" / "config"
        create_config_file(global_path, whisper_model=global_model)

        local_path = temp_dir / ".podtext" / "config"
        create_config_file(local_path, whisper_model=local_model)

        config = load_config(create_global=False)

        assert config.whisper_model == local_model

    def test_global_used_when_no_local(self, mock_home, temp_dir, monkeypatch, clean_env):
        """Global config is used when no local config exists."""
        monkeypatch.chdir(temp_dir)

        global_path = mock_home / ".podtext" / "config"
        create_config_file(global_path, api_key="global_only_key", whisper_model="large")

        config = load_config(create_global=False)

        assert config.anthropic_key == "global_only_key"
        assert config.whisper_model == "large"


class TestProperty12EnvironmentVariablePrecedence:
    """Property 12: Environment Variable Precedence.

    For any ANTHROPIC_API_KEY environment variable value V,
    the Claude API client SHALL use V regardless of config file value.

    Validates: Requirements 8.5
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        env_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        config_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_env_var_overrides_config(self, mock_home, temp_dir, monkeypatch, env_key, config_key):
        """Environment variable ANTHROPIC_API_KEY overrides config file value."""
        monkeypatch.chdir(temp_dir)

        # Set environment variable
        monkeypatch.setenv("ANTHROPIC_API_KEY", env_key)

        # Create global config with different key
        global_path = mock_home / ".podtext" / "config"
        create_config_file(global_path, api_key=config_key)

        config = load_config(create_global=False)

        # Environment variable should win
        assert config.anthropic_key == env_key

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        env_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        global_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        local_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_env_var_overrides_both_configs(self, mock_home, temp_dir, monkeypatch, env_key, global_key, local_key):
        """Environment variable overrides both global and local config."""
        monkeypatch.chdir(temp_dir)

        monkeypatch.setenv("ANTHROPIC_API_KEY", env_key)

        global_path = mock_home / ".podtext" / "config"
        create_config_file(global_path, api_key=global_key)

        local_path = temp_dir / ".podtext" / "config"
        create_config_file(local_path, api_key=local_key)

        config = load_config(create_global=False)

        assert config.anthropic_key == env_key

    def test_config_used_when_no_env_var(self, mock_home, temp_dir, monkeypatch, clean_env):
        """Config file value is used when no environment variable is set."""
        monkeypatch.chdir(temp_dir)

        global_path = mock_home / ".podtext" / "config"
        create_config_file(global_path, api_key="config_key")

        config = load_config(create_global=False)

        assert config.anthropic_key == "config_key"
