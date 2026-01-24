# Implementation Plan: Podtext

## Overview

Implementation follows the pipeline architecture: project setup → core modules → CLI integration → testing. Each task builds incrementally, with property tests validating correctness at each stage.

## Tasks

- [x] 1. Project Setup and Configuration
  - [x] 1.1 Initialize Python 3.13 project with pyproject.toml
    - Create project structure with src/podtext layout
    - Configure pip/uv installation
    - Add dependencies: httpx, feedparser, mlx-whisper, anthropic, click, tomli
    - _Requirements: 10.1, 10.2_
  
  - [x] 1.2 Implement Config Manager
    - Create config.py with TOML loading from local/global paths
    - Implement config priority (local > global)
    - Auto-create global config with defaults if missing
    - Handle ANTHROPIC_API_KEY env var precedence
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 1.3 Write property tests for Config Manager
    - **Property 11: Config Loading Priority**
    - **Property 12: Environment Variable Precedence**
    - **Validates: Requirements 8.1, 8.2, 8.5**

- [x] 2. Discovery Module
  - [x] 2.1 Implement iTunes API Client
    - Create itunes.py with search_podcasts function
    - Parse JSON response into PodcastSearchResult objects
    - Handle API errors gracefully
    - _Requirements: 1.1, 1.5_

  - [x] 2.2 Implement RSS Feed Parser
    - Create rss.py with parse_feed function
    - Extract episode info (title, pub_date, media_url)
    - Assign index numbers to episodes
    - Handle invalid/unreachable feeds
    - _Requirements: 2.1, 2.5_

  - [x] 2.3 Write property tests for Discovery Module
    - **Property 1: Result Limiting**
    - **Property 4: RSS Parsing Validity**
    - **Validates: Requirements 1.3, 2.1, 2.3**

- [ ] 3. Checkpoint - Discovery Module Complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Media and Transcription Module
  - [ ] 4.1 Implement Media Downloader
    - Create downloader.py with download_media function
    - Store files in configured directory
    - Support temporary storage with cleanup
    - Handle download failures
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [ ] 4.2 Implement MLX-Whisper Transcriber
    - Create transcriber.py with transcribe function
    - Use configured Whisper model
    - Extract paragraph boundaries from Whisper output
    - Implement language detection with warning for non-English
    - Support skip-language-check flag
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_
  
  - [ ] 4.3 Write property tests for Media/Transcription
    - **Property 5: Media Storage Location**
    - **Property 6: Temporary File Cleanup**
    - **Property 7: Config Model Propagation**
    - **Property 9: Language Check Bypass**
    - **Validates: Requirements 3.2, 3.3, 4.2, 5.3**

- [ ] 5. Claude API Integration
  - [ ] 5.1 Implement Prompt Loader
    - Create prompts.py with load_prompts function
    - Load prompts from markdown file at runtime
    - Fall back to built-in defaults if file missing/malformed
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [ ] 5.2 Implement Claude API Client
    - Create claude.py with detect_advertisements and analyze_content functions
    - Use loaded prompts for API calls
    - Handle API unavailability gracefully
    - _Requirements: 6.1, 6.4, 7.1_
  
  - [ ] 5.3 Write property tests for Claude Integration
    - **Property 13: Prompt Runtime Loading**
    - **Validates: Requirements 9.2**

- [ ] 6. Output Generation
  - [ ] 6.1 Implement Advertisement Removal
    - Create processor.py with remove_advertisements function
    - Remove identified ad blocks from text
    - Insert "ADVERTISEMENT WAS REMOVED" markers
    - _Requirements: 6.2, 6.3_
  
  - [ ] 6.2 Implement Markdown Generator
    - Create output.py with generate_markdown function
    - Create frontmatter with episode metadata and analysis results
    - Include transcribed text with paragraph formatting
    - _Requirements: 4.4, 4.5, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [ ] 6.3 Write property tests for Output Generation
    - **Property 8: Markdown Output Completeness**
    - **Property 10: Advertisement Removal with Markers**
    - **Validates: Requirements 4.4, 4.5, 6.2, 6.3, 7.6**

- [ ] 7. Checkpoint - Core Modules Complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. CLI Interface
  - [ ] 8.1 Implement CLI Commands
    - Create cli.py with Click command group
    - Implement `search` command with --limit option
    - Implement `episodes` command with --limit option
    - Implement `transcribe` command with --skip-language-check flag
    - _Requirements: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4_
  
  - [ ] 8.2 Write property tests for CLI Display
    - **Property 2: Search Result Display Completeness**
    - **Property 3: Episode Display Completeness**
    - **Validates: Requirements 1.2, 2.2**
  
  - [ ] 8.3 Wire Pipeline Together
    - Create pipeline.py to orchestrate full transcription flow
    - Connect: download → transcribe → analyze → output
    - Handle errors at each stage appropriately
    - _Requirements: 3.1, 4.1, 6.1, 7.1_

- [ ] 9. Final Integration
  - [ ] 9.1 Create Entry Point
    - Configure console_scripts in pyproject.toml
    - Ensure `podtext` command is available after install
    - _Requirements: 10.2_
  
  - [ ] 9.2 Write integration tests
    - Test end-to-end flow with mocked external APIs
    - Test config file creation on first run
    - Test error handling paths
    - _Requirements: 10.4_

- [ ] 10. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property tests are required
- Property tests use Hypothesis with minimum 100 iterations
- External APIs (iTunes, Claude) should be mocked in tests
- MLX-Whisper tests may require audio fixtures or mocking
