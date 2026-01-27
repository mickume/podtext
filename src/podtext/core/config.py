"""Configuration management for Podtext.

Handles TOML configuration loading from local and global paths,
with environment variable precedence for sensitive values.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Configuration file paths
LOCAL_CONFIG_PATH = Path(".podtext/config")
GLOBAL_CONFIG_PATH = Path.home() / ".podtext" / "config"

# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "anthropic_key": "",
    },
    "storage": {
        "media_dir": ".podtext/downloads/",
        "output_dir": ".podtext/output/",
        "temp_storage": False,
    },
    "whisper": {
        "model": "base",
    },
}

# Valid Whisper model names
VALID_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large"}


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""


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
class Config:
    """Main configuration container.

    Holds all configuration settings for Podtext, loaded from
    local and global config files with environment variable overrides.
    """

    api: ApiConfig = field(default_factory=ApiConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)

    def get_anthropic_key(self) -> str:
        """Get the Anthropic API key with environment variable precedence.

        Returns:
            The API key from ANTHROPIC_API_KEY env var if set,
            otherwise the value from config file.

        Validates: Requirements 8.5
        """
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if env_key:
            return env_key
        return self.api.anthropic_key

    def get_media_dir(self) -> Path:
        """Get the media directory as a Path object."""
        return Path(self.storage.media_dir)

    def get_output_dir(self) -> Path:
        """Get the output directory as a Path object."""
        return Path(self.storage.output_dir)


def _generate_default_config_toml() -> str:
    """Generate default configuration as TOML string.

    Returns:
        TOML-formatted string with default configuration values.
    """
    return """# Podtext Configuration File

[api]
# Anthropic API key for Claude integration
# Environment variable ANTHROPIC_API_KEY takes precedence
anthropic_key = ""

[storage]
# Directory for downloaded media files
media_dir = ".podtext/downloads/"
# Directory for output transcripts
output_dir = ".podtext/output/"
# Delete media files after transcription completes
temp_storage = false

[whisper]
# Whisper model to use: tiny, base, small, medium, large
model = "base"
"""


def _ensure_local_config_exists(local_path: Path) -> None:
    """Create local config file with defaults if it doesn't exist.

    Args:
        local_path: Path to the local config file.

    Validates: Requirements 8.3
    """
    if not local_path.exists():
        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)
        # Write default configuration
        local_path.write_text(_generate_default_config_toml())


def _load_toml_file(path: Path) -> dict[str, Any]:
    """Load and parse a TOML configuration file.

    Args:
        path: Path to the TOML file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ConfigError: If the file exists but cannot be parsed.
    """
    if not path.exists():
        return {}

    try:
        content = path.read_text()
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in config file {path}: {e}") from e


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary.
        override: Dictionary with values that override base.

    Returns:
        Merged dictionary with override values taking precedence.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate_config(config_dict: dict[str, Any]) -> None:
    """Validate configuration values.

    Args:
        config_dict: Configuration dictionary to validate.

    Raises:
        ConfigError: If configuration values are invalid.
    """
    # Validate whisper model
    whisper_config = config_dict.get("whisper", {})
    model = whisper_config.get("model", "base")
    if model not in VALID_WHISPER_MODELS:
        raise ConfigError(
            f"Invalid whisper model '{model}'. "
            f"Valid options: {', '.join(sorted(VALID_WHISPER_MODELS))}"
        )

    # Validate storage paths are strings
    storage_config = config_dict.get("storage", {})
    for key in ["media_dir", "output_dir"]:
        value = storage_config.get(key)
        if value is not None and not isinstance(value, str):
            raise ConfigError(f"storage.{key} must be a string, got {type(value).__name__}")

    # Validate temp_storage is boolean
    temp_storage = storage_config.get("temp_storage")
    if temp_storage is not None and not isinstance(temp_storage, bool):
        raise ConfigError(
            f"storage.temp_storage must be a boolean, got {type(temp_storage).__name__}"
        )


def _dict_to_config(config_dict: dict[str, Any]) -> Config:
    """Convert configuration dictionary to Config dataclass.

    Args:
        config_dict: Configuration dictionary.

    Returns:
        Config object with values from dictionary.
    """
    api_dict = config_dict.get("api", {})
    storage_dict = config_dict.get("storage", {})
    whisper_dict = config_dict.get("whisper", {})

    return Config(
        api=ApiConfig(
            anthropic_key=api_dict.get("anthropic_key", ""),
        ),
        storage=StorageConfig(
            media_dir=storage_dict.get("media_dir", ".podtext/downloads/"),
            output_dir=storage_dict.get("output_dir", ".podtext/output/"),
            temp_storage=storage_dict.get("temp_storage", False),
        ),
        whisper=WhisperConfig(
            model=whisper_dict.get("model", "base"),
        ),
    )


def load_config(
    local_path: Path | None = None,
    global_path: Path | None = None,
    auto_create_local: bool = True,
) -> Config:
    """Load configuration from local and global config files.

    Configuration priority (highest to lowest):
    1. Local config file (.podtext/config in current directory)
    2. Global config file ($HOME/.podtext/config)
    3. Default values

    If no configuration exists, creates local config with defaults.
    Global config is never auto-created and must be set up manually by the user.

    Environment variable ANTHROPIC_API_KEY always takes precedence
    over config file values when accessed via Config.get_anthropic_key().

    Args:
        local_path: Override path for local config file.
        global_path: Override path for global config file.
        auto_create_local: If True, create local config with defaults if no config exists.

    Returns:
        Config object with merged configuration values.

    Raises:
        ConfigError: If configuration files are invalid.

    Validates: Requirements 8.1, 8.2, 8.3, 8.4
    """
    local_path = local_path or LOCAL_CONFIG_PATH
    global_path = global_path or GLOBAL_CONFIG_PATH

    # Start with defaults
    merged_config = DEFAULT_CONFIG.copy()
    merged_config = {
        "api": DEFAULT_CONFIG["api"].copy(),
        "storage": DEFAULT_CONFIG["storage"].copy(),
        "whisper": DEFAULT_CONFIG["whisper"].copy(),
    }

    # Load and merge global config (Requirement 8.1)
    global_config = _load_toml_file(global_path)
    if global_config:
        merged_config = _deep_merge(merged_config, global_config)

    # Load and merge local config - takes priority (Requirement 8.2)
    local_config = _load_toml_file(local_path)
    if local_config:
        merged_config = _deep_merge(merged_config, local_config)

    # Auto-create local config if no config exists anywhere (Requirement 8.3)
    if auto_create_local and not local_config and not global_config:
        _ensure_local_config_exists(local_path)

    # Validate the merged configuration
    _validate_config(merged_config)

    # Convert to Config dataclass
    return _dict_to_config(merged_config)


def get_config() -> Config:
    """Get the application configuration using default paths.

    Convenience function that loads configuration from standard paths.

    Returns:
        Config object with merged configuration values.

    Raises:
        ConfigError: If configuration files are invalid.
    """
    return load_config()
