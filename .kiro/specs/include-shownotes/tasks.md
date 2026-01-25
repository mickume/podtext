# Implementation Plan: Include Show Notes

## Overview

This implementation adds show notes extraction from RSS feeds and appends them to the markdown output. The work is organized into: data model updates, RSS parsing enhancement, HTML conversion utility, and output generation updates.

## Tasks

- [ ] 1. Update EpisodeInfo dataclass and RSS extraction
  - [ ] 1.1 Add `show_notes` field to EpisodeInfo dataclass
    - Add `show_notes: str = ""` field with empty default
    - Update docstring to document the new field
    - _Requirements: 1.4_
  
  - [ ] 1.2 Implement `_extract_show_notes()` function in rss.py
    - Check `entry.content[0].value` first (if exists)
    - Fall back to `entry.summary`, then `entry.description`
    - Return empty string if no fields found
    - Handle exceptions gracefully, log warnings
    - _Requirements: 1.1, 1.2, 1.3, 4.3_
  
  - [ ] 1.3 Update `_parse_feed_entries()` to populate show_notes
    - Call `_extract_show_notes()` for each entry
    - Pass result to EpisodeInfo constructor
    - _Requirements: 1.1_
  
  - [ ] 1.4 Write property test for show notes extraction priority
    - **Property 1: Show Notes Extraction Priority**
    - **Validates: Requirements 1.1, 1.2**

- [ ] 2. Implement HTML to Markdown converter
  - [ ] 2.1 Create `convert_html_to_markdown()` function in processor.py
    - Use `html.parser` module for parsing
    - Convert links: `<a href="url">text</a>` → `[text](url)`
    - Convert lists: `<ul>/<ol>/<li>` → markdown lists
    - Convert headings: `<h1>`-`<h6>` → `#` syntax
    - Convert emphasis: `<strong>/<b>` → `**`, `<em>/<i>` → `*`
    - Strip unsupported tags, preserve text content
    - Handle malformed HTML gracefully
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1_
  
  - [ ] 2.2 Write property test for HTML content preservation
    - **Property 3: HTML to Markdown Content Preservation**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
  
  - [ ] 2.3 Write property test for malformed HTML handling
    - **Property 4: Malformed HTML Graceful Handling**
    - **Validates: Requirements 4.1**

- [ ] 3. Checkpoint - Ensure extraction and conversion tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Update output generation
  - [ ] 4.1 Create `_format_show_notes()` function in output.py
    - Call `convert_html_to_markdown()` on show notes
    - Return empty string if show notes empty
    - Add "## Show Notes" heading
    - Truncate if exceeds 50,000 characters, add notice
    - _Requirements: 2.1, 2.2, 2.3, 4.2_
  
  - [ ] 4.2 Update `_format_content()` to accept show_notes parameter
    - Append formatted show notes after transcription content
    - Maintain blank line between content and show notes
    - _Requirements: 2.4_
  
  - [ ] 4.3 Update `generate_markdown()` and `generate_markdown_string()`
    - Pass `episode.show_notes` to `_format_content()`
    - _Requirements: 2.1_
  
  - [ ] 4.4 Write property test for show notes section formatting
    - **Property 2: Show Notes Section Formatting**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
  
  - [ ] 4.5 Write property test for long content truncation
    - **Property 5: Long Content Truncation**
    - **Validates: Requirements 4.2**

- [ ] 5. Unicode and integration testing
  - [ ] 5.1 Write property test for Unicode preservation
    - **Property 6: Unicode Preservation**
    - **Validates: Requirements 4.4**
  
  - [ ] 5.2 Write unit tests for edge cases
    - Test RSS entry with no show notes fields
    - Test empty show notes string
    - Test show notes at truncation boundary
    - _Requirements: 1.3, 2.3, 4.2_

- [ ] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- HTML conversion uses stdlib `html.parser` to avoid new dependencies
- Property tests use Hypothesis library (already in dev dependencies)
- All property tests are required for comprehensive coverage
