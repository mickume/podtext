# podtext

A command-line tool that turns podcast episodes into searchable, structured markdown. It downloads audio from RSS feeds, transcribes it using MLX-Whisper (optimized for Apple Silicon), and enriches the output with AI-generated summaries, topics, keywords, and advertisement detection via Claude.

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.13+
- Anthropic API key (for AI analysis features -- transcription works without it)

## Installation

```bash
git clone https://github.com/your-username/podtext.git
cd podtext

# Using uv (recommended)
uv sync

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# 1. Search for a podcast
podtext search "hard fork"

# 2. List recent episodes using the feed URL from search results
podtext episodes "https://example.com/feed.xml"

# 3. Transcribe episode #1
podtext transcribe "https://example.com/feed.xml" 1
```

The output markdown file is saved to `.podtext/output/<podcast>/<episode>.md`.

## Usage

### Search for podcasts

Find podcasts by keyword. Results include the title and RSS feed URL.

```bash
podtext search "artificial intelligence"
podtext search "tech news" --limit 5       # default: 10 results
```

### List episodes

Show recent episodes from a feed, sorted newest-first. Each episode gets an index number for use with `transcribe`.

```bash
podtext episodes "https://example.com/feed.xml"
podtext episodes "https://example.com/feed.xml" --limit 20
```

### Transcribe episodes

Transcribe one or more episodes by index. Each produces a markdown file with metadata, transcript, and (if an API key is configured) AI analysis.

```bash
# Single episode
podtext transcribe "https://example.com/feed.xml" 3

# Multiple episodes in one command (processed sequentially)
podtext transcribe "https://example.com/feed.xml" 1 3 5

# Skip language detection (useful for non-English content)
podtext transcribe "https://example.com/feed.xml" 1 --skip-language-check
```

Batch runs show progress per episode and a summary at the end. If one episode fails, the rest continue.

## Output Format

Each transcribed episode produces a markdown file:

```markdown
---
title: "Episode Title"
pub_date: "2024-01-15"
podcast: "Podcast Name"
feed_url: "https://example.com/feed.xml"
media_url: "https://example.com/episode.mp3"
topics:
  - "Topic: brief description"
keywords:
  - keyword1
  - keyword2
---

## Summary

AI-generated summary...

## Show Notes

Show notes from the RSS feed (converted from HTML)...

## Transcription

Full transcript with paragraph formatting...
```

When AI analysis is unavailable (no API key or service issues), the file still contains the transcript and show notes -- the Summary section and metadata enrichment are simply omitted.

Detected advertisements are replaced with `[ADVERTISEMENT WAS REMOVED]` markers in the transcript.

## Configuration

Podtext uses a TOML configuration file. On first run, it creates `.podtext/config` in the current directory with defaults. You can also place a global config at `~/.podtext/config` -- the local file takes precedence.

### API key

Set via environment variable (recommended):

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Or in the config file under `[api]`. The environment variable always takes precedence.

### Full configuration reference

```toml
[api]
anthropic_key = ""                    # Anthropic API key (env var preferred)

[storage]
media_dir = ".podtext/downloads/"     # Where downloaded audio is stored
output_dir = ".podtext/output/"       # Where markdown output is saved
temp_storage = false                  # Delete audio files after transcription

[whisper]
model = "base"                        # tiny, base, small, medium, large
```

Larger Whisper models produce more accurate transcriptions but are slower and use more memory. The `base` model is a good default for most podcasts.

### Prompt customization

The AI analysis prompts can be customized by editing `.podtext/prompts.md` (or `~/.podtext/prompts.md`). This file is auto-created on first run with defaults. It contains four sections that you can edit:

- **Advertisement Detection** -- how ads are identified in the transcript
- **Content Summary** -- how the episode summary is generated
- **Topic Extraction** -- how topics are identified and described
- **Keyword Extraction** -- how keywords are selected

If the file is missing or malformed, built-in defaults are used automatically.

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/ tests/
```

## License

MIT
