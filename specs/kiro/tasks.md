# Implementation Plan: Podtext

## Overview

This implementation plan breaks down the Podtext CLI tool into discrete, incremental coding tasks. Each task builds on previous work, with testing integrated throughout to validate functionality early. The implementation follows a bottom-up approach: core data models and utilities first, then individual components, and finally integration and CLI interface.

## Tasks

- [ ] 1. Set up project structure and core data models
  - Create Python package structure with `src/podtext/` directory
  - Set up `pyproject.toml` with dependencies (mlx-whisper, anthropic, click, tomli, hypothesis, pytest)
  - Define all dataclass models in `models.py` (PodcastResult, Episode, TranscriptionResult, TranscriptionSegment, AdSegment, AnalysisResult, EpisodeMetadata, Config, TranscribeFlags)
  - Create `__init__.py` files for package structure
  - _Requirements: 11.1, 11.3, 11.4_

- [ ] 1.1 Write property tests for data models
  - **Property 23: Configuration Round-Trip**
  - **Validates: Requirements 7.10**

- [ ] 2. Implement platform detection
  - [ ] 2.1 Create `platform.py` with Apple Silicon detection
    - Implement `is_apple_silicon()` using `platform.machine()` to check for 'arm64' on Darwin
    - Implement `verify_platform_or_exit()` that checks platform and exits with error message if not Apple Silicon
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 2.2 Write unit tests for platform detection
    - Test detection on mocked Apple Silicon platform
    - Test warning and exit on mocked non-Apple Silicon platform
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 3. Implement configuration management
  - [ ] 3.1 Create `config.py` with configuration loading logic
    - Implement `create_default_config()` to write default TOML config
    - Implement `load_config()` with priority: CLI flags > env vars > local config > home config > defaults
    - Handle config file search order (.podtext/config, then $HOME/.podtext/config)
    - Create $HOME/.podtext/config if no config exists
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

  - [ ] 3.2 Write property tests for configuration
    - **Property 21: Configuration Field Presence**
    - **Validates: Requirements 7.4**
    - **Property 22: Configuration Priority**
    - **Validates: Requirements 7.9**

  - [ ] 3.3 Write unit tests for configuration
    - Test default config creation
    - Test config file search order
    - Test environment variable override
    - Test default values
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6, 7.7, 7.8_

- [ ] 4. Implement iTunes API client
  - [ ] 4.1 Create `itunes_client.py` with podcast search
    - Implement `search_podcasts()` that queries iTunes API with URL encoding
    - Parse JSON response and extract title, feed URL, and artist
    - Handle network errors with retries and clear error messages
    - _Requirements: 1.1, 1.2_

  - [ ] 4.2 Write property tests for iTunes client
    - **Property 1: iTunes API Query Construction**
    - **Validates: Requirements 1.1**
    - **Property 2: Podcast Result Extraction**
    - **Validates: Requirements 1.2**

  - [ ] 4.3 Write unit tests for iTunes client
    - Test with mocked successful API response
    - Test with mocked network error
    - Test with mocked malformed JSON response
    - _Requirements: 1.1, 1.2_

- [ ] 5. Implement RSS feed parser
  - [ ] 5.1 Create `rss_parser.py` with episode extraction
    - Implement `parse_feed()` using feedparser library
    - Extract episode title, publication date, media URL, description
    - Sort episodes by publication date (newest first)
    - Assign sequential INDEX_NUMBER starting from 1
    - Handle parsing errors with clear messages
    - _Requirements: 2.1, 2.2, 2.5_

  - [ ] 5.2 Write property tests for RSS parser
    - **Property 5: RSS Feed Parsing**
    - **Validates: Requirements 2.1**
    - **Property 6: Episode Extraction by Recency**
    - **Validates: Requirements 2.2, 2.3**
    - **Property 8: Sequential Index Assignment**
    - **Validates: Requirements 2.5**

  - [ ] 5.3 Write unit tests for RSS parser
    - Test with sample RSS feed XML
    - Test with malformed XML
    - Test with missing fields
    - Test episode ordering by date
    - _Requirements: 2.1, 2.2, 2.5_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement media downloader
  - [ ] 7.1 Create `downloader.py` with download and cleanup functions
    - Implement `download_media()` using requests with streaming
    - Show progress bar during download
    - Implement `cleanup_media()` to remove files
    - Handle network errors and disk space issues
    - _Requirements: 3.1, 3.8_

  - [ ] 7.2 Write property tests for downloader
    - **Property 9: Media Download**
    - **Validates: Requirements 3.1**
    - **Property 14: Media File Cleanup**
    - **Validates: Requirements 3.8, 3.9**

  - [ ] 7.3 Write unit tests for downloader
    - Test download with mocked HTTP response
    - Test cleanup removes file
    - Test network error handling
    - _Requirements: 3.1, 3.8_

- [ ] 8. Implement MLX-Whisper client
  - [ ] 8.1 Create `whisper_client.py` with transcription functions
    - Implement `detect_language()` using mlx_whisper
    - Implement `transcribe_audio()` with paragraph detection enabled
    - Return TranscriptionResult with text, language, and segments
    - Handle transcription errors
    - _Requirements: 3.2, 3.4, 3.5_

  - [ ] 8.2 Write property tests for Whisper client
    - **Property 10: Language Detection Invocation**
    - **Validates: Requirements 3.2**
    - **Property 11: Transcription Invocation**
    - **Validates: Requirements 3.4, 3.5**

  - [ ] 8.3 Write unit tests for Whisper client
    - Test language detection with mocked Whisper
    - Test transcription with mocked Whisper
    - Test non-English language rejection
    - _Requirements: 3.2, 3.4, 3.5_

- [ ] 9. Implement prompt management
  - [ ] 9.1 Create `prompts.py` and prompt markdown files
    - Create `prompts/analysis.md` with Claude analysis prompt template
    - Create `prompts/ad_detection.md` with ad detection prompt
    - Implement `load_prompt()` to read markdown files
    - Implement `format_prompt()` to substitute variables
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ] 9.2 Write property tests for prompt manager
    - **Property 24: Prompt File Loading**
    - **Validates: Requirements 8.3**

  - [ ] 9.3 Write unit tests for prompt manager
    - Test loading existing prompt files
    - Test error when prompt file missing
    - Test prompt formatting with variables
    - _Requirements: 8.3_

- [ ] 10. Implement Claude API client
  - [ ] 10.1 Create `claude_client.py` with analysis function
    - Implement `analyze_transcription()` using Anthropic SDK
    - Send transcription with prompts for summary, topics, keywords, and ad detection
    - Parse structured response into AnalysisResult
    - Handle API errors and rate limiting
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1_

  - [ ] 10.2 Write property tests for Claude client
    - **Property 15: Claude API Analysis Request**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
    - **Property 17: Ad Detection Request**
    - **Validates: Requirements 6.1**

  - [ ] 10.3 Write unit tests for Claude client
    - Test with mocked Claude API response
    - Test API error handling
    - Test rate limiting retry logic
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement markdown generator
  - [ ] 12.1 Create `markdown_gen.py` with generation functions
    - Implement `generate_markdown()` that creates frontmatter and body
    - Include summary, topics, keywords sections
    - Process ad segments: remove text above threshold and insert markers
    - Implement `write_markdown_file()` to write to disk
    - _Requirements: 3.6, 3.7, 5.5, 6.2, 6.3_

  - [ ] 12.2 Write property tests for markdown generator
    - **Property 12: Markdown Frontmatter Generation**
    - **Validates: Requirements 3.6**
    - **Property 13: Transcription Inclusion**
    - **Validates: Requirements 3.7**
    - **Property 16: Analysis Result Inclusion**
    - **Validates: Requirements 5.5**
    - **Property 18: Ad Segment Removal by Threshold**
    - **Validates: Requirements 6.2**
    - **Property 19: Ad Removal Marker Insertion**
    - **Validates: Requirements 6.3**

  - [ ] 12.3 Write unit tests for markdown generator
    - Test frontmatter YAML generation
    - Test ad marker insertion
    - Test ad removal with various confidence thresholds
    - Test file writing
    - _Requirements: 3.6, 3.7, 5.5, 6.2, 6.3_

- [ ] 13. Implement transcription pipeline
  - [ ] 13.1 Create `pipeline.py` with orchestration logic
    - Implement `run_transcription_pipeline()` that coordinates all steps
    - Download media → detect language → transcribe → analyze → generate markdown → cleanup
    - Handle skip_language_check flag
    - Handle remove_ads flag
    - Handle keep_media flag
    - Create output directories if needed
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7, 3.8, 3.9, 5.1, 6.1, 6.4, 10.4_

  - [ ] 13.2 Write property tests for pipeline
    - **Property 20: Ad Confidence Threshold Configuration**
    - **Validates: Requirements 6.6**
    - **Property 28: Output Directory Usage**
    - **Validates: Requirements 10.1, 10.2**
    - **Property 29: Directory Creation**
    - **Validates: Requirements 10.4**

  - [ ] 13.3 Write unit tests for pipeline
    - Test complete pipeline with all mocked dependencies
    - Test with skip_language_check flag
    - Test with no_ad_removal flag
    - Test with keep_media flag
    - Test directory creation
    - _Requirements: 3.3, 6.4, 10.3, 10.4_

- [ ] 14. Implement CLI interface
  - [ ] 14.1 Create `cli.py` with Click commands
    - Implement main command group
    - Implement `search` sub-command with --limit flag
    - Implement `episodes` sub-command with --limit flag
    - Implement `transcribe` sub-command with all flags (--no-lang-check, --no-ad-removal, --keep-media, --confidence, --output-dir)
    - Format and display results for search and episodes commands
    - Call platform verification at startup
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 1.3, 1.5, 2.4_

  - [ ] 14.2 Write property tests for CLI
    - **Property 3: Result Limiting**
    - **Validates: Requirements 1.3, 1.4**
    - **Property 4: Podcast Result Formatting**
    - **Validates: Requirements 1.5**
    - **Property 7: Episode Formatting**
    - **Validates: Requirements 2.4**
    - **Property 25: Sub-Command Routing**
    - **Validates: Requirements 9.3**
    - **Property 26: CLI Flag Parsing**
    - **Validates: Requirements 9.4**
    - **Property 27: CLI Flag Priority**
    - **Validates: Requirements 9.5**

  - [ ] 14.3 Write unit tests for CLI
    - Test search command with mocked iTunes client
    - Test episodes command with mocked RSS parser
    - Test transcribe command with mocked pipeline
    - Test flag parsing and priority
    - Test result formatting
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 1.3, 1.5, 2.4_

- [ ] 15. Create entry point and packaging
  - [ ] 15.1 Set up package entry point
    - Configure `pyproject.toml` with console_scripts entry point for `podtext` command
    - Create `__main__.py` that calls cli.main()
    - Add README.md with installation and usage instructions
    - Add LICENSE file
    - _Requirements: 11.3, 11.4_

- [ ] 16. Create custom Hypothesis strategies
  - [ ] 16.1 Create `tests/strategies.py` with custom generators
    - Implement `podcast_results()` strategy
    - Implement `episodes()` strategy
    - Implement `configs()` strategy
    - Implement `transcription_results()` strategy
    - Implement `analysis_results()` strategy
    - _Requirements: 12.1_

- [ ] 17. Final checkpoint - Run complete test suite
  - Run all unit tests and property tests
  - Verify test coverage meets 90% minimum
  - Ensure all 29 correctness properties are implemented
  - Ask the user if any issues arise

- [ ] 18. Integration testing
  - [ ] 18.1 Create integration tests
    - Test end-to-end search workflow with mocked iTunes API
    - Test end-to-end episodes workflow with mocked RSS feed
    - Test end-to-end transcription workflow with all mocked external services
    - Test configuration loading from actual TOML files
    - _Requirements: 12.2_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- All external dependencies (iTunes API, Claude API, MLX-Whisper, file system) should be mocked in tests
- Use dependency injection pattern to enable mocking
