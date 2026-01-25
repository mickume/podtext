# Design Document: Batch Transcribe

## Overview

This feature extends the existing `podtext transcribe` command to accept multiple episode indices and process them sequentially. The design maintains backward compatibility with single-episode transcription while adding batch processing capabilities. The implementation follows the existing layered architecture (CLI → Core → Services) and reuses the current transcription pipeline for each episode.

The key design principle is to minimize changes to existing code by wrapping the current single-episode processing logic in a loop, with added error handling and progress reporting.

## Architecture

### Current Architecture
```
CLI Layer (cli/main.py)
  ↓
Core Layer (core/pipeline.py)
  ↓
Services Layer (services/transcriber.py, services/claude.py, etc.)
```

### Modified Architecture
```
CLI Layer (cli/main.py)
  - Parse multiple INDEX arguments
  - Validate and deduplicate indices
  - Loop through indices
  ↓
Core Layer (core/pipeline.py)
  - Process single episode (unchanged)
  - Return success/failure status
  ↓
Services Layer (unchanged)
```

The design keeps the core pipeline unchanged and adds batch orchestration at the CLI layer.

## Components and Interfaces

### 1. CLI Command Signature (cli/main.py)

**Current Signature:**
```python
@click.command()
@click.argument('feed_url')
@click.argument('index', type=int)
@click.option('--model', default='base', help='Whisper model size')
@click.option('--output-dir', type=click.Path(), help='Output directory')
def transcribe(feed_url: str, index: int, model: str, output_dir: str | None) -> None:
    """Transcribe a podcast episode."""
```

**New Signature:**
```python
@click.command()
@click.argument('feed_url')
@click.argument('indices', nargs=-1, type=int, required=True)
@click.option('--model', default='base', help='Whisper model size')
@click.option('--output-dir', type=click.Path(), help='Output directory')
def transcribe(feed_url: str, indices: tuple[int, ...], model: str, output_dir: str | None) -> None:
    """Transcribe one or more podcast episodes."""
```

**Key Changes:**
- Rename `index` to `indices` (plural)
- Use `nargs=-1` to accept variable number of arguments
- Add `required=True` to ensure at least one index is provided
- Type changes from `int` to `tuple[int, ...]`

### 2. Batch Processing Orchestrator (cli/main.py)

**New Function:**
```python
@dataclass
class BatchResult:
    """Result of processing a single episode in a batch."""
    index: int
    success: bool
    output_path: str | None
    error_message: str | None

def process_batch(
    feed_url: str,
    indices: tuple[int, ...],
    model: str,
    output_dir: str | None
) -> list[BatchResult]:
    """
    Process multiple episodes sequentially.
    
    Args:
        feed_url: RSS feed URL
        indices: Episode indices to process
        model: Whisper model size
        output_dir: Optional output directory
        
    Returns:
        List of BatchResult objects, one per episode
    """
```

**Responsibilities:**
- Deduplicate indices while preserving order
- Iterate through indices sequentially
- Call existing pipeline for each episode
- Collect results and errors
- Display progress messages
- Return summary of results

### 3. Pipeline Interface (core/pipeline.py)

**Current Function (to be modified):**
```python
def process_episode(
    feed_url: str,
    index: int,
    model: str,
    output_dir: str | None
) -> str:
    """
    Process a single episode: download, transcribe, analyze.
    
    Returns:
        Path to output file
        
    Raises:
        Various exceptions on failure
    """
```

**Modified Function:**
```python
def process_episode(
    feed_url: str,
    index: int,
    model: str,
    output_dir: str | None
) -> str:
    """
    Process a single episode: download, transcribe, analyze.
    
    Args:
        feed_url: RSS feed URL
        index: Episode index (1-based)
        model: Whisper model size
        output_dir: Optional output directory
        
    Returns:
        Path to output file
        
    Raises:
        IndexError: If index is out of range
        TranscriptionError: If transcription fails
        DownloadError: If download fails
        ConfigError: If configuration is invalid
    """
```

**Key Changes:**
- Add explicit exception documentation
- No functional changes to the implementation
- Ensure exceptions are properly raised (not swallowed)

### 4. Progress Reporting

**Console Output Format:**
```
Processing 3 episodes from feed...

[1/3] Processing episode 5...
✓ Episode 5 transcribed successfully: .podtext/output/episode-5.md

[2/3] Processing episode 12...
✗ Episode 12 failed: Index out of range (feed has 10 episodes)

[3/3] Processing episode 8...
✓ Episode 8 transcribed successfully: .podtext/output/episode-8.md

Batch processing complete:
  ✓ 2 successful
  ✗ 1 failed
```

**Implementation:**
- Use Click's `echo()` for console output
- Use emoji/symbols for visual clarity (✓/✗)
- Show current progress (n/total)
- Display file paths for successful transcriptions
- Show error messages for failures
- Provide summary at the end

## Data Models

### BatchResult Dataclass

```python
from dataclasses import dataclass

@dataclass
class BatchResult:
    """Result of processing a single episode in a batch.
    
    Attributes:
        index: Episode index that was processed
        success: Whether processing succeeded
        output_path: Path to output file if successful, None otherwise
        error_message: Error description if failed, None otherwise
    """
    index: int
    success: bool
    output_path: str | None
    error_message: str | None
```

This dataclass encapsulates the result of processing each episode, making it easy to collect results and generate summaries.

## Error Handling

### Error Categories

1. **Validation Errors** (fail fast, before processing):
   - No indices provided → Click handles via `required=True`
   - Non-integer indices → Click handles via `type=int`
   - Negative or zero indices → Validate in `process_batch()`

2. **Per-Episode Errors** (continue processing):
   - Index out of range → Catch, log, continue
   - Download failure → Catch, log, continue
   - Transcription failure → Catch, log, continue
   - Claude API failure → Catch, log, continue (transcription still saved)

3. **Fatal Errors** (stop processing):
   - Invalid feed URL → Fail on first episode
   - Configuration errors → Fail before processing
   - File system errors (no write permission) → Fail on first episode

### Error Handling Strategy

```python
def process_batch(...) -> list[BatchResult]:
    # Validate indices
    unique_indices = deduplicate_indices(indices)
    
    results = []
    for i, index in enumerate(unique_indices, 1):
        click.echo(f"[{i}/{len(unique_indices)}] Processing episode {index}...")
        
        try:
            output_path = process_episode(feed_url, index, model, output_dir)
            results.append(BatchResult(index, True, output_path, None))
            click.echo(f"✓ Episode {index} transcribed: {output_path}")
            
        except IndexError as e:
            error_msg = f"Index out of range: {e}"
            results.append(BatchResult(index, False, None, error_msg))
            click.echo(f"✗ Episode {index} failed: {error_msg}", err=True)
            
        except (TranscriptionError, DownloadError) as e:
            error_msg = str(e)
            results.append(BatchResult(index, False, None, error_msg))
            click.echo(f"✗ Episode {index} failed: {error_msg}", err=True)
            
        except Exception as e:
            # Unexpected errors
            error_msg = f"Unexpected error: {e}"
            results.append(BatchResult(index, False, None, error_msg))
            click.echo(f"✗ Episode {index} failed: {error_msg}", err=True)
    
    return results
```

### Exit Codes

- **0**: All episodes processed successfully
- **1**: Some or all episodes failed (partial success)
- **2**: Fatal error before processing (invalid config, bad feed URL, etc.)

## Testing Strategy

The testing strategy combines unit tests for specific scenarios and property-based tests for universal correctness properties. Unit tests validate concrete examples and edge cases, while property tests verify behavior across many generated inputs.

### Unit Testing Focus
- Specific examples of batch processing (2-3 episodes)
- Edge cases: empty input, single episode, duplicate indices
- Error scenarios: invalid indices, out-of-range indices
- Integration: CLI argument parsing with Click's testing utilities
- Progress output formatting

### Property-Based Testing Focus
- Universal properties that hold for all valid inputs
- Comprehensive input coverage through randomization
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number

### Testing Tools
- **pytest**: Test framework
- **hypothesis**: Property-based testing library
- **click.testing.CliRunner**: CLI testing utilities
- **pytest-cov**: Coverage reporting

### Test Configuration
- Property tests run with minimum 100 iterations
- Each property test references its design document property
- Tag format: `# Feature: batch-transcribe, Property N: <property text>`


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Multiple Index Acceptance

*For any* non-empty list of positive integers, when provided as INDEX arguments to the transcribe command, the CLI should accept all indices without raising a validation error.

**Validates: Requirements 1.1**

### Property 2: Positive Integer Validation

*For any* list of integers containing negative numbers or zero, when provided as INDEX arguments, the CLI should reject the invalid indices and display an appropriate error message.

**Validates: Requirements 1.2**

### Property 3: Deduplication Preserves Order

*For any* list of indices containing duplicates, the processing order should contain each unique index exactly once, appearing in the position of its first occurrence in the input list.

**Validates: Requirements 1.3**

### Property 4: Sequential Processing Order

*For any* list of valid indices, the episodes should be processed in the exact order specified in the input, with each episode's processing completing before the next begins.

**Validates: Requirements 2.1**

### Property 5: Progress Display Completeness

*For any* batch of episodes being processed, the console output should contain progress indicators showing the current episode number and total count for each episode in the batch.

**Validates: Requirements 2.3, 5.2**

### Property 6: Error Isolation

*For any* batch where one or more episodes fail, the failure of any episode should not prevent the processing of subsequent episodes in the batch.

**Validates: Requirements 3.1**

### Property 7: Error Message Completeness

*For any* episode that fails during processing, the error output should contain both the episode index and a description of the failure reason.

**Validates: Requirements 3.2**

### Property 8: Summary Accuracy

*For any* completed batch, the summary display should show counts of successful and failed episodes that exactly match the actual number of successes and failures.

**Validates: Requirements 3.3, 5.4**

### Property 9: File Output Isolation

*For any* batch of successfully transcribed episodes, each episode should produce a separate output file with a unique filename.

**Validates: Requirements 4.1**

### Property 10: Naming Convention Consistency

*For any* successfully transcribed episode, the output filename should follow the existing naming convention pattern used by single-episode transcription.

**Validates: Requirements 4.2**

### Property 11: File Preservation

*For any* batch where output files already exist, running the batch again should not overwrite existing files unless the overwrite option is explicitly enabled.

**Validates: Requirements 4.3**

### Property 12: YAML Frontmatter Format

*For any* successfully transcribed episode, the output file should contain valid YAML frontmatter that matches the format used by single-episode transcription.

**Validates: Requirements 4.4**

### Property 13: Total Count Display

*For any* batch processing operation, the initial output should display the total number of unique episodes to be processed.

**Validates: Requirements 5.1**

### Property 14: Success Message with Path

*For any* successfully transcribed episode, the console output should contain a success message that includes the full path to the output file.

**Validates: Requirements 5.3**
