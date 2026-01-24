# Design Document: podtext

## Overview

podtext is a CLI tool for podcast discovery, transcription, and AI-powered analysis. This document describes the high-level architecture and component design.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           CLI Layer                              │
│                    (click-based subcommands)                     │
├─────────────────────────────────────────────────────────────────┤
│                         Core Services                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Podcast   │  │ Transcriber │  │      Analyzer           │  │
│  │   Service   │  │   Service   │  │      Service            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        Infrastructure                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Config    │  │   iTunes    │  │     Claude Client       │  │
│  │   Manager   │  │   Client    │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
podtext/
├── __init__.py
├── __main__.py          # Entry point
├── cli/
│   ├── __init__.py
│   ├── main.py          # Click app and command group
│   ├── search.py        # search subcommand
│   ├── episodes.py      # episodes subcommand
│   └── transcribe.py    # transcribe subcommand
├── services/
│   ├── __init__.py
│   ├── podcast.py       # Podcast discovery and RSS parsing
│   ├── transcriber.py   # MLX-Whisper transcription
│   └── analyzer.py      # Claude AI analysis
├── clients/
│   ├── __init__.py
│   ├── itunes.py        # iTunes Search API client
│   └── claude.py        # Claude API client wrapper
├── config/
│   ├── __init__.py
│   ├── manager.py       # Config loading and defaults
│   └── defaults.py      # Default config values
├── models/
│   ├── __init__.py
│   ├── podcast.py       # Podcast and Episode dataclasses
│   └── transcript.py    # Transcript and Analysis dataclasses
└── output/
    ├── __init__.py
    └── markdown.py      # Markdown file generation
```

## Component Descriptions

### CLI Layer (`cli/`)

Uses the `click` library for command-line parsing.

- **main.py**: Defines the `podtext` command group
- **search.py**: Implements `podtext search <term> [-n LIMIT]`
- **episodes.py**: Implements `podtext episodes <feed-url> [-n LIMIT]`
- **transcribe.py**: Implements `podtext transcribe <feed-url> <index> [--skip-language-check]`

### Services Layer (`services/`)

Business logic for core operations.

#### PodcastService
- Search podcasts via iTunes API
- Fetch and parse RSS feeds using `feedparser`
- Extract episode metadata (title, date, media URL)

#### TranscriberService
- Download media files (audio/video)
- Run MLX-Whisper transcription
- Detect language and paragraph boundaries
- Handle media cleanup

#### AnalyzerService
- Load prompts from `ANALYSIS.md`
- Call Claude API for content analysis
- Generate summary, topics, keywords
- Detect and mark advertising blocks

### Clients Layer (`clients/`)

External API integrations.

#### iTunesClient
- HTTP client for iTunes Search API
- Endpoint: `https://itunes.apple.com/search`
- Parse JSON response to extract feed URLs

#### ClaudeClient
- Wrapper around Anthropic Python SDK
- Handle API authentication
- Execute prompts and parse responses

### Config Layer (`config/`)

Configuration management.

#### ConfigManager
- Load config from `.podtext/config.toml`
- Search order: local dir → home dir
- Create defaults if missing
- Load prompts from `ANALYSIS.md`

### Models (`models/`)

Data structures using Python dataclasses.

```python
@dataclass
class Podcast:
    title: str
    feed_url: str
    author: str

@dataclass
class Episode:
    title: str
    pub_date: datetime
    media_url: str
    duration: Optional[int]

@dataclass
class Transcript:
    text: str
    paragraphs: list[str]
    language: str

@dataclass
class Analysis:
    summary: str
    topics: list[str]
    keywords: list[str]
    ad_segments: list[tuple[int, int]]  # (start, end) positions
```

### Output Layer (`output/`)

Markdown file generation.

#### MarkdownWriter
- Generate YAML frontmatter from metadata and analysis
- Format transcript with paragraph breaks
- Replace advertising segments with marker text
- Write to `<output-dir>/<podcast-name>/<episode-title>.md`

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI framework |
| `feedparser` | RSS/Atom feed parsing |
| `mlx-whisper` | Apple Silicon optimized transcription |
| `anthropic` | Claude API SDK |
| `httpx` | HTTP client for API calls |
| `tomli` / `tomllib` | TOML config parsing |
| `pyyaml` | YAML frontmatter generation |

## Data Flow

### Search Flow
```
User → CLI (search) → PodcastService → iTunesClient → iTunes API
                                    ← JSON response
                    ← list[Podcast]
     ← formatted output
```

### Episodes Flow
```
User → CLI (episodes) → PodcastService → HTTP GET → RSS Feed
                                      ← XML response
                      ← list[Episode]
     ← formatted output (with index numbers)
```

### Transcribe Flow
```
User → CLI (transcribe) → PodcastService → fetch episode by index
                                         ← Episode
                        → TranscriberService → download media
                                             → MLX-Whisper
                                             ← Transcript
                        → AnalyzerService → ClaudeClient → Claude API
                                                        ← Analysis
                        → MarkdownWriter → write file
     ← success message
```

## Configuration File Structure

### config.toml
```toml
[general]
output_dir = "./transcripts"
cleanup_media = true

[whisper]
model = "base"

[claude]
model = "claude-sonnet-4-20250514"
api_key = ""  # or use ANTHROPIC_API_KEY env var

[defaults]
search_limit = 10
episode_limit = 10
```

### ANALYSIS.md
```markdown
# Podcast Analysis Prompts

## Summary Prompt
Generate a concise summary of this podcast transcript...

## Topics Prompt
List the main topics discussed...

## Keywords Prompt
Extract relevant keywords...

## Advertising Detection Prompt
Identify advertising segments...
```

## Error Handling Strategy

- Network errors: Retry with exponential backoff, then fail gracefully with clear message
- Invalid feed URL: Validate URL format, report parsing errors
- Transcription failures: Log error, preserve partial output if available
- API rate limits: Respect rate limits, queue requests if needed
- Missing config: Create defaults, warn user about missing API keys
