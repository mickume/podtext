# Implementation Tasks: podtext

This document tracks implementation progress. Mark tasks with:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed

---

## Phase 1: Project Setup

### 1.1 Repository & Environment
- [x] Initialize Python project structure with `pyproject.toml`
- [x] Configure uv/pip for dependency management
- [x] Set up virtual environment requirements
- [x] Create package structure (`podtext/` with submodules)
- [x] Add `.gitignore` for Python projects

### 1.2 Dependencies
- [x] Add core dependencies: click, feedparser, httpx, anthropic
- [x] Add mlx-whisper for transcription
- [x] Add tomli (or use tomllib for 3.11+), pyyaml
- [x] Add development dependencies: pytest, pytest-cov, ruff

---

## Phase 2: Configuration System

### 2.1 Config Manager
- [x] Implement `config/defaults.py` with default values
- [x] Implement `config/manager.py` for TOML loading
- [x] Implement config search order (local → home)
- [x] Implement auto-creation of `$HOME/.podtext/config.toml`
- [x] Implement loading of `ANALYSIS.md` prompts file
- [x] Add unit tests for config loading and defaults

### 2.2 Default Files
- [x] Create default `config.toml` template
- [x] Create default `ANALYSIS.md` with prompt templates

---

## Phase 3: Data Models

### 3.1 Core Models
- [x] Implement `models/podcast.py` (Podcast, Episode dataclasses)
- [x] Implement `models/transcript.py` (Transcript, Analysis dataclasses)
- [x] Add unit tests for model serialization

---

## Phase 4: External Clients

### 4.1 iTunes Client
- [x] Implement `clients/itunes.py` with search functionality
- [x] Handle HTTP errors and timeouts
- [x] Parse JSON response to Podcast objects
- [x] Add unit tests with mocked responses

### 4.2 Claude Client
- [x] Implement `clients/claude.py` wrapper
- [x] Handle API key from config or environment variable
- [x] Implement prompt execution method
- [x] Handle API errors and rate limits
- [x] Add unit tests with mocked API

---

## Phase 5: Core Services

### 5.1 Podcast Service
- [x] Implement `services/podcast.py`
- [x] Implement podcast search (via iTunes client)
- [x] Implement RSS feed fetching with feedparser
- [x] Implement episode extraction and metadata parsing
- [x] Handle various RSS feed formats
- [x] Add unit tests with sample RSS feeds

### 5.2 Transcriber Service
- [x] Implement `services/transcriber.py`
- [x] Implement media file download (audio/video)
- [x] Integrate MLX-Whisper for transcription
- [x] Implement language detection
- [x] Implement paragraph boundary detection
- [x] Implement media cleanup logic
- [x] Add unit tests (mock Whisper for fast tests)

### 5.3 Analyzer Service
- [x] Implement `services/analyzer.py`
- [x] Implement summary generation
- [x] Implement topic extraction
- [x] Implement keyword extraction
- [x] Implement advertising detection
- [x] Implement ad segment removal with marker replacement
- [x] Add unit tests with sample transcripts

---

## Phase 6: Output Generation

### 6.1 Markdown Writer
- [x] Implement `output/markdown.py`
- [x] Implement YAML frontmatter generation
- [x] Implement transcript formatting with paragraphs
- [x] Implement file path generation (`<podcast>/<episode>.md`)
- [x] Implement directory creation
- [x] Sanitize filenames (remove invalid characters)
- [x] Add unit tests for output formatting

---

## Phase 7: CLI Implementation

### 7.1 CLI Framework
- [x] Implement `cli/main.py` with click command group
- [x] Implement `__main__.py` entry point
- [x] Configure CLI to load config on startup

### 7.2 Search Command
- [x] Implement `cli/search.py`
- [x] Add `-n/--limit` parameter
- [x] Format and display search results
- [x] Add integration tests

### 7.3 Episodes Command
- [x] Implement `cli/episodes.py`
- [x] Add `-n/--limit` parameter
- [x] Display episodes with index numbers
- [x] Add integration tests

### 7.4 Transcribe Command
- [x] Implement `cli/transcribe.py`
- [x] Add `--skip-language-check` flag
- [x] Orchestrate download → transcribe → analyze → write flow
- [x] Display progress feedback
- [x] Add integration tests

---

## Phase 8: Testing & Polish

### 8.1 Unit Test Coverage
- [x] Ensure all modules have unit tests
- [x] Achieve target coverage (aim for 80%+)
- [x] Add edge case tests

### 8.2 Integration Tests
- [x] Test full search → episodes → transcribe workflow
- [x] Test with real podcast feeds (selected stable feeds)
- [x] Test error scenarios (network failures, invalid URLs)

### 8.3 Documentation
- [ ] Write README.md with usage instructions
- [ ] Document configuration options
- [ ] Add example workflows

---

## Phase 9: Packaging & Distribution

### 9.1 Package Configuration
- [x] Finalize `pyproject.toml` metadata
- [x] Configure entry point for `podtext` command
- [x] Test installation via pip/uv
- [x] Verify virtual environment setup works

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
