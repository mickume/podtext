# Implementation Tasks: podtext

This document tracks implementation progress. Mark tasks with:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed

---

## Phase 1: Project Setup

### 1.1 Repository & Environment
- [ ] Initialize Python project structure with `pyproject.toml`
- [ ] Configure uv/pip for dependency management
- [ ] Set up virtual environment requirements
- [ ] Create package structure (`podtext/` with submodules)
- [ ] Add `.gitignore` for Python projects

### 1.2 Dependencies
- [ ] Add core dependencies: click, feedparser, httpx, anthropic
- [ ] Add mlx-whisper for transcription
- [ ] Add tomli (or use tomllib for 3.11+), pyyaml
- [ ] Add development dependencies: pytest, pytest-cov, ruff

---

## Phase 2: Configuration System

### 2.1 Config Manager
- [ ] Implement `config/defaults.py` with default values
- [ ] Implement `config/manager.py` for TOML loading
- [ ] Implement config search order (local → home)
- [ ] Implement auto-creation of `$HOME/.podtext/config.toml`
- [ ] Implement loading of `ANALYSIS.md` prompts file
- [ ] Add unit tests for config loading and defaults

### 2.2 Default Files
- [ ] Create default `config.toml` template
- [ ] Create default `ANALYSIS.md` with prompt templates

---

## Phase 3: Data Models

### 3.1 Core Models
- [ ] Implement `models/podcast.py` (Podcast, Episode dataclasses)
- [ ] Implement `models/transcript.py` (Transcript, Analysis dataclasses)
- [ ] Add unit tests for model serialization

---

## Phase 4: External Clients

### 4.1 iTunes Client
- [ ] Implement `clients/itunes.py` with search functionality
- [ ] Handle HTTP errors and timeouts
- [ ] Parse JSON response to Podcast objects
- [ ] Add unit tests with mocked responses

### 4.2 Claude Client
- [ ] Implement `clients/claude.py` wrapper
- [ ] Handle API key from config or environment variable
- [ ] Implement prompt execution method
- [ ] Handle API errors and rate limits
- [ ] Add unit tests with mocked API

---

## Phase 5: Core Services

### 5.1 Podcast Service
- [ ] Implement `services/podcast.py`
- [ ] Implement podcast search (via iTunes client)
- [ ] Implement RSS feed fetching with feedparser
- [ ] Implement episode extraction and metadata parsing
- [ ] Handle various RSS feed formats
- [ ] Add unit tests with sample RSS feeds

### 5.2 Transcriber Service
- [ ] Implement `services/transcriber.py`
- [ ] Implement media file download (audio/video)
- [ ] Integrate MLX-Whisper for transcription
- [ ] Implement language detection
- [ ] Implement paragraph boundary detection
- [ ] Implement media cleanup logic
- [ ] Add unit tests (mock Whisper for fast tests)

### 5.3 Analyzer Service
- [ ] Implement `services/analyzer.py`
- [ ] Implement summary generation
- [ ] Implement topic extraction
- [ ] Implement keyword extraction
- [ ] Implement advertising detection
- [ ] Implement ad segment removal with marker replacement
- [ ] Add unit tests with sample transcripts

---

## Phase 6: Output Generation

### 6.1 Markdown Writer
- [ ] Implement `output/markdown.py`
- [ ] Implement YAML frontmatter generation
- [ ] Implement transcript formatting with paragraphs
- [ ] Implement file path generation (`<podcast>/<episode>.md`)
- [ ] Implement directory creation
- [ ] Sanitize filenames (remove invalid characters)
- [ ] Add unit tests for output formatting

---

## Phase 7: CLI Implementation

### 7.1 CLI Framework
- [ ] Implement `cli/main.py` with click command group
- [ ] Implement `__main__.py` entry point
- [ ] Configure CLI to load config on startup

### 7.2 Search Command
- [ ] Implement `cli/search.py`
- [ ] Add `-n/--limit` parameter
- [ ] Format and display search results
- [ ] Add integration tests

### 7.3 Episodes Command
- [ ] Implement `cli/episodes.py`
- [ ] Add `-n/--limit` parameter
- [ ] Display episodes with index numbers
- [ ] Add integration tests

### 7.4 Transcribe Command
- [ ] Implement `cli/transcribe.py`
- [ ] Add `--skip-language-check` flag
- [ ] Orchestrate download → transcribe → analyze → write flow
- [ ] Display progress feedback
- [ ] Add integration tests

---

## Phase 8: Testing & Polish

### 8.1 Unit Test Coverage
- [ ] Ensure all modules have unit tests
- [ ] Achieve target coverage (aim for 80%+)
- [ ] Add edge case tests

### 8.2 Integration Tests
- [ ] Test full search → episodes → transcribe workflow
- [ ] Test with real podcast feeds (selected stable feeds)
- [ ] Test error scenarios (network failures, invalid URLs)

### 8.3 Documentation
- [ ] Write README.md with usage instructions
- [ ] Document configuration options
- [ ] Add example workflows

---

## Phase 9: Packaging & Distribution

### 9.1 Package Configuration
- [ ] Finalize `pyproject.toml` metadata
- [ ] Configure entry point for `podtext` command
- [ ] Test installation via pip/uv
- [ ] Verify virtual environment setup works

---

## Task Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Config) ──→ Phase 3 (Models)
    ↓                    ↓
Phase 4 (Clients) ←──────┘
    ↓
Phase 5 (Services)
    ↓
Phase 6 (Output)
    ↓
Phase 7 (CLI)
    ↓
Phase 8 (Testing)
    ↓
Phase 9 (Packaging)
```

---

## Notes

- Phases 2-4 can be partially parallelized
- Unit tests should be written alongside each component
- Integration tests require all components to be complete
- Consider mocking MLX-Whisper in tests to avoid long transcription times
