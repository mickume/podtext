# Implementation Plan: Enhanced Metadata

## Overview

This implementation adds feed_url and media_url fields to the YAML frontmatter in transcription output. The changes span three files with minimal modifications to maintain backward compatibility.

## Tasks

- [ ] 1. Extend EpisodeInfo dataclass
  - [ ] 1.1 Add optional feed_url field to EpisodeInfo dataclass
    - Add `feed_url: str | None = None` field after `media_url`
    - Update docstring to document the new field
    - _Requirements: 4.1_
  
  - [ ] 1.2 Write property test for EpisodeInfo with feed_url
    - **Property 4: Parse Feed Populates Feed URL**
    - Test that dataclass accepts feed_url as optional parameter
    - **Validates: Requirements 4.1, 4.2**

- [ ] 2. Update RSS parser to populate feed_url
  - [ ] 2.1 Modify _parse_feed_entries to accept feed_url parameter
    - Add `feed_url: str` parameter to function signature
    - Pass feed_url when creating EpisodeInfo instances
    - _Requirements: 4.2_
  
  - [ ] 2.2 Update parse_feed to pass feed_url to _parse_feed_entries
    - Pass the input feed_url to _parse_feed_entries call
    - _Requirements: 4.2_
  
  - [ ] 2.3 Write property test for parse_feed feed_url population
    - **Property 4: Parse Feed Populates Feed URL**
    - Verify all returned EpisodeInfo have feed_url set to input URL
    - **Validates: Requirements 4.2**

- [ ] 3. Checkpoint - Verify data layer changes
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Update frontmatter generation
  - [ ] 4.1 Add feed_url to _format_frontmatter output
    - Add conditional inclusion of feed_url when episode.feed_url is not None
    - Place after podcast field, before media_url
    - _Requirements: 1.1, 1.2_
  
  - [ ] 4.2 Add media_url to _format_frontmatter output
    - Add media_url field (always present since media_url is required)
    - Place after feed_url, before summary
    - _Requirements: 2.1, 2.2_
  
  - [ ] 4.3 Update _format_frontmatter docstring
    - Document new feed_url and media_url fields
    - Update example output in docstring
    - _Requirements: 3.1_
  
  - [ ] 4.4 Write property tests for frontmatter generation
    - **Property 1: Feed URL Round-Trip**
    - **Property 2: Media URL Round-Trip**
    - **Property 3: Existing Fields Preserved**
    - **Validates: Requirements 1.1, 1.3, 2.1, 2.2, 3.1, 3.2**

- [ ] 5. Update generate_markdown docstring
  - [ ] 5.1 Update example in generate_markdown docstring
    - Update the example output to show new frontmatter fields
    - _Requirements: 3.1_

- [ ] 6. Final checkpoint - Verify all changes
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property tests are required
- The media_url field already exists in EpisodeInfo, only frontmatter output needs updating
- feed_url is optional to maintain backward compatibility with existing code
- Property tests use hypothesis library with minimum 100 iterations
