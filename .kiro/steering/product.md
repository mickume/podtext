# Podtext Product Overview

Podtext is a CLI tool for podcast transcription and analysis, optimized for Apple Silicon Macs.

## Core Workflow

1. **Discover** - Search podcasts via iTunes API by keywords, title, or author
2. **Browse** - List episodes from RSS feeds with publication dates
3. **Transcribe** - Download, transcribe (MLX-Whisper), and analyze (Claude AI)

## Key Features

- MLX-Whisper transcription (Apple M-series optimized)
- Claude AI integration for:
  - Content summarization
  - Topic and keyword extraction
  - Advertisement detection and removal
- Markdown output with YAML frontmatter
- Configurable via TOML files (local `.podtext/config` or global `~/.podtext/config`)

## Target Users

Researchers, knowledge workers and also Agents/MCP servers that work on behalve of the formentioned users, who convert podcast audio to searchable, analyzable text.