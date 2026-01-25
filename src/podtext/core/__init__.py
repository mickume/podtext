"""Core modules for Podtext."""

from podtext.core.config import (
    ApiConfig,
    Config,
    ConfigError,
    StorageConfig,
    WhisperConfig,
    get_config,
    load_config,
)
from podtext.core.prompts import (
    Prompts,
    PromptsError,
    generate_default_prompts_markdown,
    get_prompts,
    load_prompts,
)
from podtext.core.processor import (
    ADVERTISEMENT_MARKER,
    remove_advertisements,
)

__all__ = [
    "ApiConfig",
    "Config",
    "ConfigError",
    "StorageConfig",
    "WhisperConfig",
    "get_config",
    "load_config",
    "Prompts",
    "PromptsError",
    "generate_default_prompts_markdown",
    "get_prompts",
    "load_prompts",
    "ADVERTISEMENT_MARKER",
    "remove_advertisements",
]
