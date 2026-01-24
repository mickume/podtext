# podtext

A command-line podcast transcription and analysis tool optimized for Apple Silicon.

## Features

- **Podcast Discovery**: Search for podcasts using the iTunes API
- **Episode Listing**: Browse episodes from any podcast RSS feed
- **Audio Transcription**: Transcribe audio using MLX-Whisper (optimized for Apple M-series chips)
- **AI Analysis**: Analyze transcripts with Claude AI for summaries, topics, and keywords
- **Advertising Detection**: Automatically detect and mark advertising content
- **Markdown Output**: Generate clean markdown files with metadata and transcripts

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.13+
- FFmpeg (for audio extraction from video files)

## Installation

### Using pip

```bash
pip install -e .
```

### Using uv (recommended)

```bash
uv pip install -e .
```

### Development installation

```bash
# Clone the repository
git clone https://github.com/podtext/podtext.git
cd podtext

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"
```

## Configuration

### API Key Setup

Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

Or add it to your configuration file.

### Configuration File

podtext looks for configuration in the following order:
1. `.podtext/config.toml` in the current directory
2. `$HOME/.podtext/config.toml`

Example configuration:

```toml
[general]
download_dir = "./downloads"
output_dir = "./transcripts"
keep_media = false
verbosity = "normal"

[transcription]
whisper_model = "base"  # tiny, base, small, medium, large
skip_language_check = false

[analysis]
claude_model = "claude-sonnet-4-20250514"
ad_confidence_threshold = 0.9

[defaults]
search_limit = 10
episode_limit = 10
```

## Usage

### Search for podcasts

```bash
podtext search "software engineering"
podtext search "The Tim Ferriss Show" --limit 5
```

### List episodes from a feed

```bash
podtext episodes "https://example.com/feed.xml"
podtext episodes "https://example.com/feed.xml" --limit 20
```

### Process an episode

```bash
# Download, transcribe, and analyze episode #1 (most recent)
podtext process "https://example.com/feed.xml" 1

# Keep the downloaded media file
podtext process "https://example.com/feed.xml" 1 --keep-media

# Skip language verification
podtext process "https://example.com/feed.xml" 1 --skip-language-check
```

### Re-process a local file

```bash
podtext reprocess ./episode.mp3 --podcast-title "My Podcast" --episode-title "Episode 1"
```

### Verbosity options

```bash
podtext -v search "test"    # Verbose output
podtext -q search "test"    # Quiet mode
podtext --error-only search "test"  # Errors only
```

## Output

Transcripts are saved as markdown files with YAML frontmatter:

```markdown
---
title: "Episode Title"
podcast: "Podcast Name"
date: 2024-01-15
keywords: [keyword1, keyword2, keyword3]
language: en
duration: 45:30
---

# Episode Title

**Podcast:** Podcast Name
**Published:** January 15, 2024

## Summary

AI-generated summary of the episode...

## Topics Covered

- Topic 1: Description
- Topic 2: Description

## Keywords

keyword1, keyword2, keyword3

## Transcript

Full transcript text with [ADVERTISING REMOVED] markers...
```

## Development

### Running tests

```bash
pytest
```

### Running tests with coverage

```bash
pytest --cov=podtext --cov-report=html
```

### Linting

```bash
ruff check .
ruff format .
```

### Type checking

```bash
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.
