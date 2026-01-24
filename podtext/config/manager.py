"""Configuration manager for podtext."""

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .defaults import (
    ANALYSIS_FILE_NAME,
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CLEANUP_MEDIA,
    DEFAULT_EPISODE_LIMIT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_WHISPER_MODEL,
    VALID_WHISPER_MODELS,
    get_default_analysis_md,
    get_default_config_toml,
)


@dataclass
class AnalysisPrompts:
    """Container for analysis prompts loaded from ANALYSIS.md."""

    summary: str = ""
    topics: str = ""
    keywords: str = ""
    advertising: str = ""


@dataclass
class Config:
    """Application configuration."""

    # General settings
    output_dir: str = DEFAULT_OUTPUT_DIR
    cleanup_media: bool = DEFAULT_CLEANUP_MEDIA

    # Whisper settings
    whisper_model: str = DEFAULT_WHISPER_MODEL

    # Claude settings
    claude_model: str = DEFAULT_CLAUDE_MODEL
    claude_api_key: str = ""

    # CLI defaults
    search_limit: int = DEFAULT_SEARCH_LIMIT
    episode_limit: int = DEFAULT_EPISODE_LIMIT

    # Prompts
    prompts: AnalysisPrompts = field(default_factory=AnalysisPrompts)

    # Config location info
    config_dir: Path | None = None

    def get_api_key(self) -> str:
        """Get Claude API key from config or environment."""
        if self.claude_api_key:
            return self.claude_api_key
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def validate(self) -> list[str]:
        """Validate configuration and return list of warnings."""
        warnings = []

        if self.whisper_model not in VALID_WHISPER_MODELS:
            warnings.append(
                f"Invalid whisper_model '{self.whisper_model}'. "
                f"Valid options: {', '.join(VALID_WHISPER_MODELS)}"
            )

        if not self.get_api_key():
            warnings.append(
                "No Claude API key configured. "
                "Set claude.api_key in config or ANTHROPIC_API_KEY environment variable."
            )

        return warnings


class ConfigManager:
    """Manages configuration loading and persistence."""

    def __init__(self, local_dir: Path | None = None):
        """Initialize config manager.

        Args:
            local_dir: Local directory to check for config (defaults to cwd)
        """
        self.local_dir = local_dir or Path.cwd()
        self._config: Config | None = None

    def get_config_path(self) -> Path:
        """Get the path to the config file.

        Search order: local directory, then home directory.
        """
        # Check local directory first
        local_config = self.local_dir / CONFIG_DIR_NAME / CONFIG_FILE_NAME
        if local_config.exists():
            return local_config

        # Fall back to home directory
        return Path.home() / CONFIG_DIR_NAME / CONFIG_FILE_NAME

    def get_analysis_path(self) -> Path:
        """Get the path to the ANALYSIS.md file."""
        config_path = self.get_config_path()
        return config_path.parent / ANALYSIS_FILE_NAME

    def load(self) -> Config:
        """Load configuration from file.

        Creates default config in home directory if none exists.
        """
        if self._config is not None:
            return self._config

        config_path = self.get_config_path()

        # Create default config if it doesn't exist
        if not config_path.exists():
            self._create_default_config()
            config_path = self.get_config_path()

        # Load config
        config = self._load_toml(config_path)

        # Load prompts
        analysis_path = self.get_analysis_path()
        if not analysis_path.exists():
            self._create_default_analysis(analysis_path.parent)

        config.prompts = self._load_prompts(analysis_path)
        config.config_dir = config_path.parent

        self._config = config
        return config

    def _create_default_config(self) -> None:
        """Create default configuration in home directory."""
        home_config_dir = Path.home() / CONFIG_DIR_NAME
        home_config_dir.mkdir(exist_ok=True)

        config_file = home_config_dir / CONFIG_FILE_NAME
        config_file.write_text(get_default_config_toml())

        self._create_default_analysis(home_config_dir)

    def _create_default_analysis(self, config_dir: Path) -> None:
        """Create default ANALYSIS.md file."""
        analysis_file = config_dir / ANALYSIS_FILE_NAME
        if not analysis_file.exists():
            analysis_file.write_text(get_default_analysis_md())

    def _load_toml(self, path: Path) -> Config:
        """Load configuration from TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        config = Config()

        # General settings
        general = data.get("general", {})
        if "output_dir" in general:
            config.output_dir = general["output_dir"]
        if "cleanup_media" in general:
            config.cleanup_media = general["cleanup_media"]

        # Whisper settings
        whisper = data.get("whisper", {})
        if "model" in whisper:
            config.whisper_model = whisper["model"]

        # Claude settings
        claude = data.get("claude", {})
        if "model" in claude:
            config.claude_model = claude["model"]
        if "api_key" in claude:
            config.claude_api_key = claude["api_key"]

        # Default settings
        defaults = data.get("defaults", {})
        if "search_limit" in defaults:
            config.search_limit = defaults["search_limit"]
        if "episode_limit" in defaults:
            config.episode_limit = defaults["episode_limit"]

        return config

    def _load_prompts(self, path: Path) -> AnalysisPrompts:
        """Load prompts from ANALYSIS.md file."""
        if not path.exists():
            return AnalysisPrompts()

        content = path.read_text()
        prompts = AnalysisPrompts()

        # Parse markdown sections
        sections = self._parse_markdown_sections(content)

        prompts.summary = sections.get("summary prompt", "")
        prompts.topics = sections.get("topics prompt", "")
        prompts.keywords = sections.get("keywords prompt", "")
        prompts.advertising = sections.get("advertising detection prompt", "")

        return prompts

    def _parse_markdown_sections(self, content: str) -> dict[str, str]:
        """Parse markdown content into sections by ## headers."""
        sections: dict[str, str] = {}

        # Split by ## headers
        pattern = r"^## (.+)$"
        parts = re.split(pattern, content, flags=re.MULTILINE)

        # parts[0] is content before first ##, then alternating header/content
        for i in range(1, len(parts) - 1, 2):
            header = parts[i].strip().lower()
            section_content = parts[i + 1].strip()
            sections[header] = section_content

        return sections

    def reload(self) -> Config:
        """Force reload configuration from disk."""
        self._config = None
        return self.load()
