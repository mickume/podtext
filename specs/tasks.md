# podtext Implementation Tasks

This document tracks implementation progress for podtext.

## Document Information

- **Version**: 1.0
- **Status**: Complete
- **Design**: specs/design.md
- **Requirements**: specs/requirements.md

---

## Progress Overview

| Phase | Description | Status | Progress |
|-------|-------------|--------|----------|
| 1 | Project Setup | Complete | 8/8 |
| 2 | Core Layer | Complete | 10/10 |
| 3 | Discovery Service | Complete | 8/8 |
| 4 | Download Service | Complete | 7/7 |
| 5 | Transcription Service | Complete | 8/8 |
| 6 | Analysis Service | Complete | 10/10 |
| 7 | Output Service | Complete | 6/6 |
| 8 | CLI Implementation | Complete | 12/12 |
| 9 | Integration & Polish | Complete | 8/8 |

**Total: 77/77 tasks complete**

---

## Phase 1: Project Setup

### 1.1 Project Initialization

- [x] **T1.1.1** Create `pyproject.toml` with project metadata and dependencies
  - Python 3.13 requirement
  - All dependencies from design doc
  - Entry point configuration
  
- [x] **T1.1.2** Create project directory structure per design doc
  - `src/podtext/` with subpackages
  - `tests/` directory
  - `prompts/` directory

- [x] **T1.1.3** Create `README.md` with basic project description
  - Installation instructions
  - Quick start guide

- [x] **T1.1.4** Set up development dependencies
  - pytest, pytest-cov
  - ruff (linting)
  - mypy (type checking)

### 1.2 Virtual Environment & Tooling

- [x] **T1.2.1** Create virtual environment setup script
  - Support both pip and uv

- [x] **T1.2.2** Configure ruff for linting
  - Create `ruff.toml` or configure in `pyproject.toml`

- [x] **T1.2.3** Configure mypy for type checking
  - Strict mode for src/
  
- [x] **T1.2.4** Set up pytest configuration
  - Coverage reporting
  - Test discovery

**Phase 1 Exit Criteria:**
- [x] `pip install -e .` works
- [x] `pytest` runs (with no tests yet)
- [x] `ruff check .` passes
- [x] `mypy src/` passes

---

## Phase 2: Core Layer

### 2.1 Data Models

- [x] **T2.1.1** Implement `Podcast` dataclass
  - Fields: title, feed_url, author, description, artwork_url
  - REQ-1.1.3

- [x] **T2.1.2** Implement `Episode` dataclass
  - Fields: index, title, published, media_url, duration, description
  - REQ-2.1.4

- [x] **T2.1.3** Implement `Segment` and `Transcript` dataclasses
  - Segment: text, start, end
  - Transcript: segments, language, duration, full_text property
  - REQ-4.3.1

- [x] **T2.1.4** Implement `AdvertisingBlock` and `Analysis` dataclasses
  - AdvertisingBlock: start_index, end_index, confidence
  - Analysis: summary, topics, keywords, advertising_blocks
  - REQ-5.2.x, REQ-5.3.x

- [x] **T2.1.5** Implement `EpisodeOutput` dataclass
  - Combines all data for output generation
  - REQ-6.1.x

- [x] **T2.1.6** Write unit tests for all models

### 2.2 Configuration

- [x] **T2.2.1** Implement `Config` class with Pydantic
  - Define all settings from design doc
  - Default values
  - REQ-7.1.1

- [x] **T2.2.2** Implement configuration loading with precedence
  - Local `.podtext/config.toml` first
  - User `$HOME/.podtext/config.toml` second
  - Built-in defaults
  - REQ-7.1.2, REQ-7.1.3

- [x] **T2.2.3** Implement `ensure_user_config()` function
  - Create default config if missing
  - REQ-7.1.4

- [x] **T2.2.4** Write unit tests for configuration

### 2.3 Error Handling

- [x] **T2.3.1** Implement exception hierarchy
  - PodtextError base class
  - ConfigError, DiscoveryError, DownloadError
  - TranscriptionError, AnalysisError, OutputError
  - REQ-9.2.1, REQ-9.2.2

**Phase 2 Exit Criteria:**
- [x] All models instantiable and serializable
- [x] Config loads from files correctly
- [x] All unit tests pass

---

## Phase 3: Discovery Service

### 3.1 iTunes Search

- [x] **T3.1.1** Implement iTunes API client
  - HTTP request to search endpoint
  - Parse JSON response
  - REQ-1.1.1, REQ-1.1.2

- [x] **T3.1.2** Implement `search_podcasts()` method
  - Query parameter handling
  - Limit parameter (default 10)
  - Return list of Podcast
  - REQ-1.1.4, REQ-1.1.5

- [x] **T3.1.3** Write unit tests with mocked API responses

### 3.2 RSS Feed Parsing

- [x] **T3.2.1** Implement RSS feed fetcher
  - HTTP request to feed URL
  - Error handling for invalid/unreachable URLs
  - REQ-1.2.1

- [x] **T3.2.2** Implement RSS parser with feedparser
  - Extract episode data
  - Handle various RSS formats
  - REQ-2.1.1

- [x] **T3.2.3** Implement `get_episodes()` method
  - Limit parameter (default 10)
  - Index assignment (1 = most recent)
  - Return list of Episode
  - REQ-2.1.2, REQ-2.1.3, REQ-2.1.5

- [x] **T3.2.4** Write unit tests with sample RSS feeds

### 3.3 Integration

- [x] **T3.3.1** Create `DiscoveryService` class combining both features
  - REQ-1.2.2 (public feeds only)

**Phase 3 Exit Criteria:**
- [x] Can search iTunes and get Podcast list
- [x] Can parse RSS feed and get Episode list
- [x] All unit tests pass

---

## Phase 4: Download Service

### 4.1 Media Download

- [x] **T4.1.1** Implement media file downloader
  - HTTP download with progress
  - Save to configured directory
  - REQ-3.1.1, REQ-3.1.2

- [x] **T4.1.2** Implement download error handling
  - Abort on failure (no resume)
  - Clear error messages
  - REQ-3.1.4

- [x] **T4.1.3** Write unit tests with mocked downloads

### 4.2 Audio Extraction

- [x] **T4.2.1** Implement video detection
  - Check file extension/MIME type

- [x] **T4.2.2** Implement audio extraction with ffmpeg
  - Extract audio track from video
  - REQ-3.1.3

- [x] **T4.2.3** Write unit tests for audio extraction

### 4.3 File Management

- [x] **T4.3.1** Implement cleanup function
  - Delete media files after processing
  - Respect keep_media config
  - REQ-3.2.1, REQ-3.2.2

**Phase 4 Exit Criteria:**
- [x] Can download media files
- [x] Can extract audio from video
- [x] Cleanup works correctly
- [x] All unit tests pass

---

## Phase 5: Transcription Service

### 5.1 MLX-Whisper Integration

- [x] **T5.1.1** Implement Whisper model loading
  - Model selection from config
  - Default to "base"
  - REQ-4.1.2, REQ-4.1.3

- [x] **T5.1.2** Implement `transcribe()` method
  - MLX-Whisper transcription
  - Return Transcript with segments
  - REQ-4.1.1

- [x] **T5.1.3** Implement segment extraction
  - Use Whisper's sentence/segment boundaries
  - Create Segment objects with timestamps
  - REQ-4.3.1

- [x] **T5.1.4** Write unit tests with sample audio

### 5.2 Language Detection

- [x] **T5.2.1** Implement `detect_language()` method
  - Use Whisper's language detection
  - REQ-4.2.1

- [x] **T5.2.2** Implement language check logic
  - Warn if not English
  - Continue with transcription
  - REQ-4.2.2

- [x] **T5.2.3** Implement skip-language-check flag
  - REQ-4.2.3

- [x] **T5.2.4** Write unit tests for language detection

**Phase 5 Exit Criteria:**
- [x] Can transcribe audio files
- [x] Language detection works
- [x] Segments have correct timestamps
- [x] All unit tests pass

---

## Phase 6: Analysis Service

### 6.1 Claude API Setup

- [x] **T6.1.1** Implement API key resolution
  - Check ANTHROPIC_API_KEY env var first
  - Fall back to config file
  - REQ-5.1.2, REQ-5.1.3

- [x] **T6.1.2** Implement Claude client initialization
  - Model selection from config
  - Default to claude-sonnet (latest)
  - REQ-5.1.1, REQ-5.1.4, REQ-5.1.5

- [x] **T6.1.3** Write unit tests with mocked API

### 6.2 Prompt Management

- [x] **T6.2.1** Create `prompts/analysis.md` file
  - Summary prompt
  - Topics prompt
  - Keywords prompt
  - Advertising detection prompt
  - REQ-7.2.1

- [x] **T6.2.2** Implement `PromptManager` class
  - Parse markdown sections
  - Get prompt by name
  - REQ-7.2.2

- [x] **T6.2.3** Write unit tests for prompt loading

### 6.3 Analysis Features

- [x] **T6.3.1** Implement summary generation
  - Call Claude API with transcript
  - REQ-5.2.1

- [x] **T6.3.2** Implement topic extraction
  - Return list of one-sentence topics
  - REQ-5.2.2

- [x] **T6.3.3** Implement keyword extraction
  - Return list of keywords
  - REQ-5.2.3

- [x] **T6.3.4** Implement advertising detection
  - Analyze transcript sections
  - Return AdvertisingBlock list with confidence
  - REQ-5.3.1, REQ-5.3.2, REQ-5.3.3, REQ-5.3.4

**Phase 6 Exit Criteria:**
- [x] Can generate summary, topics, keywords
- [x] Advertising detection returns confidence scores
- [x] Prompts are editable without code changes
- [x] All unit tests pass

---

## Phase 7: Output Service

### 7.1 Filename Generation

- [x] **T7.1.1** Implement filename generator
  - Pattern: {podcast-name}-{episode-title}.md
  - Truncate to ~50 characters
  - Sanitize for filesystem
  - REQ-6.1.3, REQ-6.1.4

- [x] **T7.1.2** Write unit tests for filename generation

### 7.2 Markdown Generation

- [x] **T7.2.1** Implement YAML frontmatter generation
  - title, publication date, keywords
  - REQ-6.1.2

- [x] **T7.2.2** Implement transcript formatting
  - Apply advertising removal markers
  - Segment paragraphs appropriately
  - REQ-5.3.2

- [x] **T7.2.3** Implement full markdown output
  - Frontmatter + summary + topics + transcript
  - REQ-6.1.1, REQ-6.1.5

- [x] **T7.2.4** Write unit tests for markdown generation

**Phase 7 Exit Criteria:**
- [x] Generates valid markdown with frontmatter
- [x] Filenames are correctly truncated
- [x] Advertising markers inserted correctly
- [x] All unit tests pass

---

## Phase 8: CLI Implementation

### 8.1 CLI Framework Setup

- [x] **T8.1.1** Set up Typer application
  - Main app with subcommands
  - Rich integration for output

- [x] **T8.1.2** Implement global options
  - --verbose, --quiet, --error-only
  - --config PATH
  - REQ-9.1.1, REQ-9.1.2

- [x] **T8.1.3** Implement verbosity handling
  - Configure Rich console based on level
  - REQ-9.1.3, REQ-9.1.4, REQ-9.1.5

### 8.2 Search Command

- [x] **T8.2.1** Implement `search` command
  - Query argument
  - --limit option
  - REQ-1.1.x

- [x] **T8.2.2** Implement search results display
  - Table format with title and feed URL
  - REQ-1.1.3

- [x] **T8.2.3** Write CLI tests for search

### 8.3 Episodes Command

- [x] **T8.3.1** Implement `episodes` command
  - Feed URL argument
  - --limit option
  - REQ-2.1.x

- [x] **T8.3.2** Implement episode list display
  - Table with index, title, date
  - REQ-2.1.4

- [x] **T8.3.3** Write CLI tests for episodes

### 8.4 Process Command

- [x] **T8.4.1** Implement `process` command
  - Feed URL and index arguments
  - --skip-language-check, --keep-media options
  - REQ-3.x, REQ-4.x, REQ-5.x, REQ-6.x

- [x] **T8.4.2** Implement processing pipeline orchestration
  - Call services in correct order
  - Progress display

- [x] **T8.4.3** Write CLI tests for process

### 8.5 Reprocess Command

- [x] **T8.5.1** Implement `reprocess` command
  - Media file path argument
  - --podcast-title, --episode-title options
  - REQ-8.1.1, REQ-8.1.2

- [x] **T8.5.2** Write CLI tests for reprocess

**Phase 8 Exit Criteria:**
- [x] All commands work end-to-end
- [x] Verbosity levels work correctly
- [x] Help text is clear and complete
- [x] All CLI tests pass

---

## Phase 9: Integration & Polish

### 9.1 Integration Testing

- [x] **T9.1.1** Create integration test suite
  - End-to-end workflow tests
  - Mocked external APIs

- [x] **T9.1.2** Test configuration precedence
  - Local > user > defaults

- [x] **T9.1.3** Test error handling paths
  - Invalid URLs, API failures, etc.

### 9.2 Documentation

- [x] **T9.2.1** Complete README.md
  - Full installation instructions
  - Usage examples for all commands
  - Configuration reference

- [x] **T9.2.2** Add inline code documentation
  - Docstrings for public APIs
  - Type hints throughout

### 9.3 Final Polish

- [x] **T9.3.1** Ensure test coverage > 80%
  - REQ-10.2.1, REQ-10.2.2

- [x] **T9.3.2** Fix any remaining linter errors

- [x] **T9.3.3** Verify pip/uv installation works
  - Clean install test
  - REQ-10.1.2

- [x] **T9.3.4** Final manual testing
  - Test with real podcasts
  - Verify output quality

**Phase 9 Exit Criteria:**
- [x] All tests pass
- [x] Documentation complete
- [x] Clean install works
- [x] Tool functions correctly with real data

---

## Appendix: Requirement Traceability

| Task | Requirements |
|------|--------------|
| T1.x | REQ-10.1.1, REQ-10.1.2, REQ-10.1.3 |
| T2.1.x | REQ-1.1.3, REQ-2.1.4, REQ-4.3.1, REQ-5.2.x, REQ-5.3.x, REQ-6.1.x |
| T2.2.x | REQ-7.1.x |
| T2.3.x | REQ-9.2.x |
| T3.1.x | REQ-1.1.x, REQ-1.1.6 |
| T3.2.x | REQ-1.2.x, REQ-2.1.x |
| T4.x | REQ-3.x |
| T5.x | REQ-4.x |
| T6.x | REQ-5.x, REQ-7.2.x |
| T7.x | REQ-6.x |
| T8.x | REQ-9.1.x |
| T9.x | REQ-10.2.x |
