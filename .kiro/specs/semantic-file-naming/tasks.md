# Implementation Plan: Semantic File Naming

## Overview

This plan implements hierarchical output file naming with sanitized podcast subdirectories and episode filenames. The implementation adds a `sanitize_path_component()` utility and updates the pipeline to generate paths in the format `<output-dir>/<podcast-name>/<episode-title>.md`.

## Tasks

- [ ] 1. Implement path sanitization utility
  - [ ] 1.1 Add `sanitize_path_component()` function to `src/podtext/core/processor.py`
    - Replace invalid characters (`/ \ : * ? " < > |`) with underscores
    - Collapse consecutive underscores into single underscore
    - Trim leading/trailing whitespace and underscores
    - Truncate to max_length (default 30), preferring word boundaries
    - Return fallback value if result is empty
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.3_

  - [ ] 1.2 Write property tests for sanitization in `tests/test_processor_properties.py`
    - **Property 2: Sanitization Correctness**
    - **Property 3: Length Constraint**
    - **Property 5: Sanitization Round-Trip Stability (Idempotence)**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 4.3**

  - [ ] 1.3 Write unit tests for sanitization edge cases in `tests/test_processor.py`
    - Test empty string returns fallback
    - Test string with only invalid characters returns fallback
    - Test valid characters are preserved
    - Test truncation at word boundaries
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 2. Update pipeline path generation
  - [ ] 2.1 Replace `_generate_output_filename()` with `_generate_output_path()` in `src/podtext/core/pipeline.py`
    - Accept episode, podcast_name, and output_dir parameters
    - Use `sanitize_path_component()` for podcast name (fallback: "unknown-podcast")
    - Use `sanitize_path_component()` for episode title (fallback: "episode_{index}")
    - Return full Path: `output_dir / safe_podcast / f"{safe_title}.md"`
    - _Requirements: 1.1, 4.1, 4.2, 4.4_

  - [ ] 2.2 Update `run_pipeline()` to use new path generation
    - Call `_generate_output_path()` when output_path is None
    - Pass podcast_name parameter to path generator
    - Directory creation handled by `generate_markdown()` (already calls `mkdir(parents=True)`)
    - _Requirements: 1.1, 1.2, 5.1, 5.2_

  - [ ] 2.3 Write property test for path format in `tests/test_pipeline_properties.py`
    - **Property 1: Path Format Structure**
    - **Validates: Requirements 1.1**

  - [ ] 2.4 Write unit tests for path generation in `tests/test_pipeline.py`
    - Test path structure with valid podcast name and episode title
    - Test fallback for empty podcast name
    - Test fallback for empty episode title
    - Test custom output_path override
    - _Requirements: 1.1, 4.1, 4.2, 4.4, 5.1_

- [ ] 3. Checkpoint - Verify implementation
  - Ensure all tests pass, ask the user if questions arise.
  - Run `pytest tests/test_processor.py tests/test_pipeline.py -v`
  - Run `mypy src/podtext/core/processor.py src/podtext/core/pipeline.py`

## Notes

- All tasks are required including property-based tests and unit tests
- The existing `generate_markdown()` in `output.py` already handles directory creation via `output_path.parent.mkdir(parents=True, exist_ok=True)`
- Property tests use Hypothesis with minimum 100 iterations
- All functions require type hints for mypy strict mode compliance
