# Implementation Plan: Batch Transcribe

## Overview

This implementation extends the existing `podtext transcribe` command to accept multiple episode indices and process them sequentially. The approach minimizes changes to existing code by adding batch orchestration at the CLI layer while reusing the current single-episode pipeline. All changes are contained within `cli/main.py` and new test files.

## Tasks

- [x] 1. Create BatchResult dataclass for tracking episode processing results
  - Add `BatchResult` dataclass to `cli/main.py` with fields: index, success, output_path, error_message
  - Add type hints and docstring
  - _Requirements: 3.3, 5.4_

- [x] 2. Implement index deduplication utility
  - [x] 2.1 Create `deduplicate_indices()` function that preserves first occurrence order
    - Accept tuple of integers, return list of unique integers in order
    - _Requirements: 1.3_
  
  - [x] 2.2 Write property test for deduplication order preservation
    - **Property 3: Deduplication Preserves Order**
    - **Validates: Requirements 1.3**

- [x] 3. Modify CLI command signature to accept multiple indices
  - [x] 3.1 Update `@click.argument` from `index` to `indices` with `nargs=-1, required=True`
    - Change parameter name from `index: int` to `indices: tuple[int, ...]`
    - Update docstring to reflect multiple episode support
    - _Requirements: 1.1, 1.4, 1.5_
  
  - [x] 3.2 Write unit tests for CLI argument parsing
    - Test single index (backward compatibility)
    - Test multiple indices
    - Test empty input (should error)
    - _Requirements: 1.1, 1.4, 1.5_

- [x] 4. Implement batch processing orchestrator
  - [x] 4.1 Create `process_batch()` function in `cli/main.py`
    - Accept feed_url, indices tuple, model, output_dir
    - Deduplicate indices
    - Display initial message with total count
    - Loop through indices sequentially
    - Return list of BatchResult objects
    - _Requirements: 2.1, 5.1_
  
  - [x] 4.2 Add per-episode processing with error handling
    - Wrap `process_episode()` call in try-except block
    - Catch IndexError, TranscriptionError, DownloadError, and generic Exception
    - Create BatchResult for each episode (success or failure)
    - Continue processing on errors
    - _Requirements: 3.1, 3.4_
  
  - [x] 4.3 Add progress and result reporting
    - Display "[n/total] Processing episode X..." before each episode
    - Display "✓ Episode X transcribed: <path>" on success
    - Display "✗ Episode X failed: <error>" on failure
    - _Requirements: 2.3, 3.2, 5.2, 5.3_
  
  - [x] 4.4 Write property test for sequential processing order
    - **Property 4: Sequential Processing Order**
    - **Validates: Requirements 2.1**
  
  - [x] 4.5 Write property test for error isolation
    - **Property 6: Error Isolation**
    - **Validates: Requirements 3.1**

- [x] 5. Implement batch summary display
  - [x] 5.1 Create `display_summary()` function
    - Accept list of BatchResult objects
    - Count successes and failures
    - Display formatted summary with counts
    - _Requirements: 3.3, 5.4_
  
  - [x] 5.2 Write property test for summary accuracy
    - **Property 8: Summary Accuracy**
    - **Validates: Requirements 3.3, 5.4**

- [x] 6. Update main transcribe command to use batch processing
  - [x] 6.1 Modify `transcribe()` command function
    - Call `process_batch()` instead of direct `process_episode()`
    - Call `display_summary()` with results
    - Set exit code based on results (0 if all success, 1 if any failures)
    - _Requirements: 3.5_
  
  - [x] 6.2 Write unit test for exit codes
    - Test exit code 0 when all episodes succeed
    - Test exit code 1 when some/all episodes fail
    - _Requirements: 3.5_

- [x] 7. Checkpoint - Ensure all tests pass
  - Run `pytest` to verify all tests pass
  - Run `mypy src/podtext` to verify type checking
  - Ensure all tests pass, ask the user if questions arise

- [x] 8. Add property tests for output validation
  - [x] 8.1 Write property test for file output isolation
    - **Property 9: File Output Isolation**
    - **Validates: Requirements 4.1**
  
  - [x] 8.2 Write property test for naming convention consistency
    - **Property 10: Naming Convention Consistency**
    - **Validates: Requirements 4.2**
  
  - [x] 8.3 Write property test for YAML frontmatter format
    - **Property 12: YAML Frontmatter Format**
    - **Validates: Requirements 4.4**

- [x] 9. Add property tests for console output validation
  - [x] 9.1 Write property test for progress display completeness
    - **Property 5: Progress Display Completeness**
    - **Validates: Requirements 2.3, 5.2**
  
  - [x] 9.2 Write property test for error message completeness
    - **Property 7: Error Message Completeness**
    - **Validates: Requirements 3.2**
  
  - [x] 9.3 Write property test for total count display
    - **Property 13: Total Count Display**
    - **Validates: Requirements 5.1**
  
  - [x] 9.4 Write property test for success message with path
    - **Property 14: Success Message with Path**
    - **Validates: Requirements 5.3**

- [x] 10. Add input validation property tests
  - [x] 10.1 Write property test for multiple index acceptance
    - **Property 1: Multiple Index Acceptance**
    - **Validates: Requirements 1.1**
  
  - [x] 10.2 Write property test for positive integer validation
    - **Property 2: Positive Integer Validation**
    - **Validates: Requirements 1.2**

- [x] 11. Final checkpoint - Run full test suite and verify functionality
  - Run `pytest --cov=src/podtext` to verify coverage
  - Run `ruff check src tests` to verify linting
  - Test manually with real podcast feed
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Each task references specific requirements for traceability
- The implementation reuses existing `process_episode()` function without modification
- All batch orchestration logic is contained in `cli/main.py`
- Property tests use Hypothesis library with minimum 100 iterations
- Checkpoints ensure incremental validation of core functionality
