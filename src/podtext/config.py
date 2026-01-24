"""Configuration management for Podtext."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli
import tomli_w


@dataclass
class ApiConfig:
    """API configuration settings."""

    anthropic_key: str = ""


@dataclass
class StorageConfig:
    """Storage configuration settings."""

    media_dir: str = ".podtext/downloads/"
    output_dir: str = ".podtext/output/"
    temp_storage: bool = False


@dataclass
class WhisperConfig:
    """Whisper model configuration settings."""

    model: str = "base"


@dataclass
class PodtextConfig:
    """Complete Podtext configuration."""

    api: ApiConfig = field(default_factory=ApiConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)


# Default configuration as TOML
DEFAULT_CONFIG_TOML = """\
[api]
anthropic_key = ""  # Optional, env var ANTHROPIC_API_KEY takes precedence

[storage]
media_dir = ".podtext/downloads/"
output_dir = ".podtext/output/"
temp_storage = false  # Delete media after transcription

[whisper]
model = "base"  # tiny, base, small, medium, large
"""


def get_local_config_path() -> Path:
    """Get the local configuration file path (.podtext/config in current directory)."""
    return Path.cwd() / ".podtext" / "config"


def get_global_config_path() -> Path:
    """Get the global configuration file path ($HOME/.podtext/config)."""
    return Path.home() / ".podtext" / "config"


def _parse_config_dict(data: dict[str, Any]) -> PodtextConfig:
    """Parse a dictionary into PodtextConfig."""
    api_data = data.get("api", {})
    storage_data = data.get("storage", {})
    whisper_data = data.get("whisper", {})

    return PodtextConfig(
        api=ApiConfig(
            anthropic_key=api_data.get("anthropic_key", ""),
        ),
        storage=StorageConfig(
            media_dir=storage_data.get("media_dir", ".podtext/downloads/"),
            output_dir=storage_data.get("output_dir", ".podtext/output/"),
            temp_storage=storage_data.get("temp_storage", False),
        ),
        whisper=WhisperConfig(
            model=whisper_data.get("model", "base"),
        ),
    )


def _merge_configs(base: PodtextConfig, override: PodtextConfig) -> PodtextConfig:
    """Merge two configs, with override taking precedence for non-default values."""
    return PodtextConfig(
        api=ApiConfig(
            anthropic_key=override.api.anthropic_key or base.api.anthropic_key,
        ),
        storage=StorageConfig(
            media_dir=override.storage.media_dir
            if override.storage.media_dir != ".podtext/downloads/"
            else base.storage.media_dir,
            output_dir=override.storage.output_dir
            if override.storage.output_dir != ".podtext/output/"
            else base.storage.output_dir,
            temp_storage=override.storage.temp_storage or base.storage.temp_storage,
        ),
        whisper=WhisperConfig(
            model=override.whisper.model if override.whisper.model != "base" else base.whisper.model,
        ),
    )


def _load_config_file(path: Path) -> PodtextConfig | None:
    """Load configuration from a TOML file."""
    if not path.exists():
        return None

    try:
        with open(path, "rb") as f:
            data = tomli.load(f)
        return _parse_config_dict(data)
    except (tomli.TOMLDecodeError, OSError):
        return None


def _create_default_global_config(path: Path) -> None:
    """Create the global config file with default values if it doesn't exist."""
    if path.exists():
        return

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write default config
    default_data = {
        "api": {"anthropic_key": ""},
        "storage": {
            "media_dir": ".podtext/downloads/",
            "output_dir": ".podtext/output/",
            "temp_storage": False,
        },
        "whisper": {"model": "base"},
    }

    with open(path, "wb") as f:
        tomli_w.dump(default_data, f)


def load_config(
    local_path: Path | None = None,
    global_path: Path | None = None,
    create_global_if_missing: bool = True,
) -> PodtextConfig:
    """
    Load configuration with priority: local > global > defaults.

    Environment variable ANTHROPIC_API_KEY takes precedence over config file values.

    Args:
        local_path: Path to local config file (default: .podtext/config)
        global_path: Path to global config file (default: $HOME/.podtext/config)
        create_global_if_missing: Whether to create global config if it doesn't exist

    Returns:
        Merged configuration with environment variable overrides applied
    """
    if local_path is None:
        local_path = get_local_config_path()
    if global_path is None:
        global_path = get_global_config_path()

    # Create global config with defaults if it doesn't exist
    if create_global_if_missing:
        _create_default_global_config(global_path)

    # Start with defaults
    config = PodtextConfig()

    # Load global config
    global_config = _load_config_file(global_path)
    if global_config is not None:
        config = global_config

    # Load and merge local config (local takes precedence)
    local_config = _load_config_file(local_path)
    if local_config is not None:
        # For local config priority, we use local values when they differ from defaults
        config = _merge_with_local_priority(config, local_config)

    # Apply environment variable override for API key
    env_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_api_key:
        config.api.anthropic_key = env_api_key

    return config


def _merge_with_local_priority(global_config: PodtextConfig, local_config: PodtextConfig) -> PodtextConfig:
    """Merge configs with local taking full priority over global."""
    # Local config values always win if the local config file exists
    return PodtextConfig(
        api=ApiConfig(
            anthropic_key=local_config.api.anthropic_key
            if local_config.api.anthropic_key
            else global_config.api.anthropic_key,
        ),
        storage=StorageConfig(
            media_dir=local_config.storage.media_dir,
            output_dir=local_config.storage.output_dir,
            temp_storage=local_config.storage.temp_storage,
        ),
        whisper=WhisperConfig(
            model=local_config.whisper.model,
        ),
    )


def get_anthropic_api_key(config: PodtextConfig) -> str | None:
    """
    Get the Anthropic API key with environment variable precedence.

    Args:
        config: The loaded configuration

    Returns:
        The API key if available, None otherwise
    """
    # Environment variable takes precedence (already applied in load_config)
    if config.api.anthropic_key:
        return config.api.anthropic_key
    return None
