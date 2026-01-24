"""Default configuration values for podtext."""

from pathlib import Path

# General settings
DEFAULT_OUTPUT_DIR = "./transcripts"
DEFAULT_CLEANUP_MEDIA = True

# Whisper settings
DEFAULT_WHISPER_MODEL = "base"
VALID_WHISPER_MODELS = ("tiny", "base", "small", "medium", "large")

# Claude settings
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"

# CLI defaults
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_EPISODE_LIMIT = 10

# Config file names
CONFIG_DIR_NAME = ".podtext"
CONFIG_FILE_NAME = "config.toml"
ANALYSIS_FILE_NAME = "ANALYSIS.md"


def get_default_config() -> dict:
    """Return the default configuration dictionary."""
    return {
        "general": {
            "output_dir": DEFAULT_OUTPUT_DIR,
            "cleanup_media": DEFAULT_CLEANUP_MEDIA,
        },
        "whisper": {
            "model": DEFAULT_WHISPER_MODEL,
        },
        "claude": {
            "model": DEFAULT_CLAUDE_MODEL,
            "api_key": "",
        },
        "defaults": {
            "search_limit": DEFAULT_SEARCH_LIMIT,
            "episode_limit": DEFAULT_EPISODE_LIMIT,
        },
    }


def get_default_config_toml() -> str:
    """Return the default config.toml content as a string."""
    return '''# podtext configuration file

[general]
# Directory where transcripts will be saved
output_dir = "./transcripts"

# Delete media files after successful transcription
cleanup_media = true

[whisper]
# MLX-Whisper model size: tiny, base, small, medium, large
model = "base"

[claude]
# Claude API model to use for analysis
model = "claude-sonnet-4-20250514"

# API key (leave empty to use ANTHROPIC_API_KEY environment variable)
api_key = ""

[defaults]
# Default number of search results to show
search_limit = 10

# Default number of episodes to show
episode_limit = 10
'''


def get_default_analysis_md() -> str:
    """Return the default ANALYSIS.md content."""
    return '''# Podcast Analysis Prompts

This file contains the prompts used by podtext for AI-powered analysis.
You can customize these prompts to change how the analysis works.

## Summary Prompt

Generate a concise summary of this podcast transcript in 2-3 paragraphs.
Focus on the main themes, key insights, and notable discussions.
Write in a neutral, informative tone.

## Topics Prompt

List the main topics discussed in this podcast episode.
Provide each topic as a single sentence that captures its essence.
Return the topics as a bullet-point list.
Aim for 3-7 topics depending on episode content.

## Keywords Prompt

Extract relevant keywords from this podcast transcript.
Include names of people, organizations, products, concepts, and themes discussed.
Return keywords as a comma-separated list.
Aim for 10-20 keywords that would help with categorization and search.

## Advertising Detection Prompt

Analyze this podcast transcript and identify any advertising or sponsored content segments.
Look for:
- Host-read advertisements
- Sponsor mentions and endorsements
- Mid-roll ad segments
- Product promotions that are clearly paid content

For each advertising segment found, provide:
1. The approximate start and end of the segment (by quoting the first and last few words)
2. The advertiser or product being promoted
3. Your confidence level (high, medium, low)

Only flag segments you are confident are advertisements, not organic product discussions.
'''


def get_config_dir(local_dir: Path | None = None) -> Path:
    """Get the configuration directory path.

    Checks local directory first, then falls back to home directory.
    """
    if local_dir:
        local_config = local_dir / CONFIG_DIR_NAME
        if local_config.exists():
            return local_config

    # Check current directory
    cwd_config = Path.cwd() / CONFIG_DIR_NAME
    if cwd_config.exists():
        return cwd_config

    # Fall back to home directory
    return Path.home() / CONFIG_DIR_NAME
