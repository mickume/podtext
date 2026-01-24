"""Configuration management for podtext."""

import os
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found, no-redef]


class Verbosity(str, Enum):
    """Verbosity levels for CLI output."""

    QUIET = "quiet"
    ERROR = "error"
    NORMAL = "normal"
    VERBOSE = "verbose"


class GeneralConfig(BaseModel):
    """General configuration settings."""

    download_dir: str = Field(default="./downloads")
    output_dir: str = Field(default="./transcripts")
    keep_media: bool = Field(default=False)
    verbosity: Verbosity = Field(default=Verbosity.NORMAL)


class TranscriptionConfig(BaseModel):
    """Transcription settings."""

    whisper_model: str = Field(default="base")
    skip_language_check: bool = Field(default=False)


class AnalysisConfig(BaseModel):
    """Claude API analysis settings."""

    claude_model: str = Field(default="claude-sonnet-4-20250514")
    ad_confidence_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    api_key: str | None = Field(default=None)


class DefaultsConfig(BaseModel):
    """Default values for CLI commands."""

    search_limit: int = Field(default=10, ge=1)
    episode_limit: int = Field(default=10, ge=1)


class Config(BaseModel):
    """Main configuration class."""

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)

    @classmethod
    def load(cls, config_path: str | None = None) -> Self:
        """
        Load config with precedence:
        1. Explicit config path (if provided)
        2. .podtext/config.toml (local)
        3. $HOME/.podtext/config.toml (user)
        4. Built-in defaults
        """
        if config_path:
            path = Path(config_path)
            if path.exists():
                return cls._load_from_file(path)

        # Try local config
        local_config = Path(".podtext/config.toml")
        if local_config.exists():
            return cls._load_from_file(local_config)

        # Try user config
        user_config = cls._user_config_path()
        if user_config.exists():
            return cls._load_from_file(user_config)

        # Return defaults
        return cls()

    @classmethod
    def _load_from_file(cls, path: Path) -> Self:
        """Load configuration from a TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    @classmethod
    def _user_config_path(cls) -> Path:
        """Get the user configuration file path."""
        return Path.home() / ".podtext" / "config.toml"

    @classmethod
    def ensure_user_config(cls) -> Path:
        """Create $HOME/.podtext/config.toml if missing, return path."""
        config_path = cls._user_config_path()
        if not config_path.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(cls._default_config_content())
        return config_path

    @staticmethod
    def _default_config_content() -> str:
        """Generate default configuration file content."""
        return """\
# podtext configuration file

[general]
download_dir = "./downloads"      # Relative to cwd or absolute
output_dir = "./transcripts"      # Where to save markdown files
keep_media = false                # Keep media files after processing
verbosity = "normal"              # quiet, error, normal, verbose

[transcription]
whisper_model = "base"            # tiny, base, small, medium, large
skip_language_check = false       # Skip English verification

[analysis]
claude_model = "claude-sonnet-4-20250514"
ad_confidence_threshold = 0.9     # 0.0 to 1.0
# api_key = "sk-..."              # Optional, prefer ANTHROPIC_API_KEY env var

[defaults]
search_limit = 10                 # Default podcast search results
episode_limit = 10                # Default episode list size
"""


def get_api_key(config: Config) -> str:
    """
    Get Claude API key with precedence:
    1. ANTHROPIC_API_KEY environment variable
    2. config.analysis.api_key
    3. Raise ConfigError
    """
    from podtext.core.errors import ConfigError

    # Check environment variable first
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key

    # Check config file
    if config.analysis.api_key:
        return config.analysis.api_key

    raise ConfigError(
        "No API key found. Set ANTHROPIC_API_KEY environment variable "
        "or add api_key to the [analysis] section of your config file."
    )


def get_prompts_file() -> Path:
    """Get the path to the prompts file."""
    # First check local
    local_prompts = Path("prompts/analysis.md")
    if local_prompts.exists():
        return local_prompts

    # Check user directory
    user_prompts = Path.home() / ".podtext" / "prompts" / "analysis.md"
    if user_prompts.exists():
        return user_prompts

    # Check package directory
    package_prompts = Path(__file__).parent.parent.parent.parent / "prompts" / "analysis.md"
    if package_prompts.exists():
        return package_prompts

    raise FileNotFoundError("Could not find prompts/analysis.md")
