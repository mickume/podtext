# podtext

A CLI tool for podcast discovery, transcription, and AI-powered analysis. Optimized for Apple Silicon (M-series chips) using MLX-Whisper for fast local transcription.

## Features

- **Podcast Search**: Find podcasts via the iTunes Search API
- **Episode Listing**: Browse recent episodes from any RSS feed
- **Local Transcription**: Transcribe episodes using MLX-Whisper on Apple Silicon
- **AI Analysis**: Generate summaries, topics, and keywords using Claude AI
- **Advertising Detection**: Automatically detect and optionally remove sponsor content
- **Markdown Output**: Export transcripts with metadata as organized markdown files

## Installation

Requires Python 3.13+ and Apple Silicon (M1/M2/M3/M4).

```bash
# Clone the repository
git clone https://github.com/your-username/podtext.git
cd podtext

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Quick Start

### 1. Search for Podcasts

```bash
podtext search "technology"
```

This searches the iTunes podcast directory and displays matching podcasts with their feed URLs.

### 2. List Episodes

```bash
podtext episodes "https://feeds.simplecast.com/Y8_HoeNW"
```

Shows recent episodes with index numbers for transcription.

### 3. Transcribe an Episode

```bash
podtext transcribe "https://feeds.simplecast.com/Y8_HoeNW" 1
```

Downloads, transcribes, and analyzes the specified episode. The output is saved as a markdown file.

## Commands

### `podtext search <term>`

Search for podcasts matching the given term.

Options:
- `-n, --limit`: Maximum number of results (default: 10)

Example:
```bash
podtext search "science podcast" -n 20
```

### `podtext episodes <feed-url>`

List recent episodes from a podcast RSS feed.

Options:
- `-n, --limit`: Maximum number of episodes to show (default: 10)

Example:
```bash
podtext episodes "https://example.com/feed.xml" -n 15
```

### `podtext transcribe <feed-url> <index>`

Download and transcribe a podcast episode.

Arguments:
- `feed-url`: RSS feed URL of the podcast
- `index`: Episode number from the `episodes` command output (1-based)

Options:
- `--skip-language-check`: Skip language verification warning
- `--skip-analysis`: Skip AI analysis (transcription only)
- `-n, --limit`: Episode limit for index mapping

Example:
```bash
# Full transcription with AI analysis
podtext transcribe "https://example.com/feed.xml" 1

# Transcription only (no AI analysis)
podtext transcribe "https://example.com/feed.xml" 3 --skip-analysis
```

## Configuration

Configuration files are stored in `.podtext/` directory.

### Config File Location

podtext searches for configuration in this order:
1. `./.podtext/config.toml` (current directory)
2. `$HOME/.podtext/config.toml` (home directory)

If no configuration exists, default files are created in your home directory.

### config.toml

```toml
[general]
# Directory where transcripts will be saved
output_dir = "./transcripts"

# Delete media files after successful transcription
cleanup_media = true

[whisper]
# MLX-Whisper model size: tiny, base, small, medium, large
# Larger models are more accurate but slower
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
```

### ANALYSIS.md

The `ANALYSIS.md` file contains the prompts used for AI analysis. You can customize these to change how summaries, topics, keywords, and advertising detection work.

### Environment Variables

- `ANTHROPIC_API_KEY`: Claude API key for AI analysis (required for analysis features)

## Output Format

Transcripts are saved as markdown files with YAML frontmatter:

```markdown
---
title: Episode Title
podcast: Podcast Name
date: 2024-03-20T10:00:00
language: en
duration: 1:30:45
keywords:
  - topic1
  - topic2
topics:
  - First main topic discussed
  - Second main topic discussed
---

# Episode Title

## Summary

AI-generated summary of the episode content...

## Topics

- First main topic discussed
- Second main topic discussed

## Transcript

Full transcript text with paragraph breaks...
```

## Example Workflow

```bash
# 1. Search for a podcast about AI
podtext search "artificial intelligence"

# 2. Get the feed URL from results and list episodes
podtext episodes "https://feeds.example.com/ai-podcast.xml"

# 3. Transcribe the most recent episode
podtext transcribe "https://feeds.example.com/ai-podcast.xml" 1

# 4. Find your transcript
ls transcripts/AI\ Podcast/
```

## Whisper Models

Available model sizes (in order of speed vs accuracy):

| Model | Speed | Accuracy | VRAM |
|-------|-------|----------|------|
| tiny | Fastest | Basic | ~1GB |
| base | Fast | Good | ~1GB |
| small | Medium | Better | ~2GB |
| medium | Slow | Great | ~5GB |
| large | Slowest | Best | ~10GB |

Configure in `config.toml`:
```toml
[whisper]
model = "small"
```

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --all-extras

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=podtext --cov-report=html
```

### Code Quality

```bash
# Run linter
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

## Requirements

- Python 3.13+
- Apple Silicon Mac (M1, M2, M3, or M4)
- Anthropic API key (for AI analysis features)

## License

MIT License
