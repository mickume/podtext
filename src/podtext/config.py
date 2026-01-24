"""Configuration management for Podtext.

Handles loading configuration from local (.podtext/config) and global
($HOME/.podtext/config) TOML files with appropriate priority.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli


@dataclass
class Config:
    """Application configuration."""

    # API settings
    anthropic_key: str = ""

    # Storage settings
    media_dir: Path = field(default_factory=lambda: Path(".podtext/downloads/"))
    output_dir: Path = field(default_factory=lambda: Path(".podtext/output/"))
    temp_storage: bool = False

    # Whisper settings
    whisper_model: str = "base"


# Default configuration as TOML
DEFAULT_CONFIG = """\
[api]
anthropic_key = ""

[storage]
media_dir = ".podtext/downloads/"
output_dir = ".podtext/output/"
temp_storage = false

[whisper]
model = "base"
"""


def get_global_config_path() -> Path:
    """Get the path to the global config file."""
    home = Path(os.environ.get("HOME", Path.home()))
    return home / ".podtext" / "config"


def get_local_config_path() -> Path:
    """Get the path to the local config file."""
    return Path(".podtext") / "config"


def _parse_config_file(path: Path) -> dict[str, Any]:
    """Parse a TOML config file.

    Returns empty dict if file doesn't exist or is invalid.
    """
    if not path.exists():
        return {}

    try:
        with open(path, "rb") as f:
            return tomli.load(f)
    except (tomli.TOMLDecodeError, OSError):
        return {}


def _merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two config dicts, with override taking priority."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def _ensure_global_config_exists() -> None:
    """Create global config with defaults if it doesn't exist."""
    global_path = get_global_config_path()
    if not global_path.exists():
        global_path.parent.mkdir(parents=True, exist_ok=True)
        global_path.write_text(DEFAULT_CONFIG)


def _dict_to_config(data: dict[str, Any]) -> Config:
    """Convert a config dict to a Config object."""
    api = data.get("api", {})
    storage = data.get("storage", {})
    whisper = data.get("whisper", {})

    return Config(
        anthropic_key=api.get("anthropic_key", ""),
        media_dir=Path(storage.get("media_dir", ".podtext/downloads/")),
        output_dir=Path(storage.get("output_dir", ".podtext/output/")),
        temp_storage=storage.get("temp_storage", False),
        whisper_model=whisper.get("model", "base"),
    )


def load_config(create_global: bool = True) -> Config:
    """Load configuration with proper priority.

    Priority order (highest to lowest):
    1. Environment variable ANTHROPIC_API_KEY
    2. Local config (.podtext/config)
    3. Global config ($HOME/.podtext/config)
    4. Defaults

    Args:
        create_global: If True, create global config with defaults if missing.

    Returns:
        Config object with merged configuration.
    """
    if create_global:
        _ensure_global_config_exists()

    # Load and merge configs
    global_config = _parse_config_file(get_global_config_path())
    local_config = _parse_config_file(get_local_config_path())

    # Merge: global serves as base, local overrides
    merged = _merge_configs(global_config, local_config)

    # Convert to Config object
    config = _dict_to_config(merged)

    # Environment variable takes precedence for API key
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        config.anthropic_key = env_key

    return config
