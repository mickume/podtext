# Requirements Document

## Introduction

This feature extends the existing `podtext transcribe` command to support batch processing of multiple podcast episodes in a single command invocation. Currently, users must run the command multiple times to transcribe multiple episodes. This enhancement allows users to specify multiple episode indices and process them sequentially, improving workflow efficiency for users who need to transcribe multiple episodes from the same feed.

## Glossary

- **CLI**: Command Line Interface - the user-facing interface for the podtext tool
- **Episode_Index**: A numeric identifier (1-based) representing an episode's position in an RSS feed
- **Transcription_Pipeline**: The complete workflow of downloading, transcribing (MLX-Whisper), and analyzing (Claude AI) a podcast episode
- **Sequential_Processing**: Processing episodes one after another in the order specified, not in parallel
- **Batch_Command**: A single CLI invocation that processes multiple episodes

## Requirements

### Requirement 1: Multiple Episode Index Input

**User Story:** As a podcast researcher, I want to specify multiple episode indices in a single command, so that I can transcribe multiple episodes without running the command repeatedly.

#### Acceptance Criteria

1. WHEN a user provides multiple INDEX arguments to the transcribe command, THE CLI SHALL accept all provided indices
2. WHEN a user provides INDEX arguments, THE CLI SHALL validate that each index is a positive integer
3. WHEN a user provides duplicate INDEX values, THE CLI SHALL process each unique index only once
4. WHEN a user provides no INDEX arguments, THE CLI SHALL return an error message indicating at least one index is required
5. THE CLI SHALL maintain backward compatibility with the single INDEX argument format

### Requirement 2: Sequential Episode Processing

**User Story:** As a podcast researcher, I want episodes to be processed one at a time in the order I specify, so that I can predict resource usage and avoid overwhelming my system.

#### Acceptance Criteria

1. WHEN multiple indices are provided, THE Transcription_Pipeline SHALL process each episode sequentially in the order specified
2. WHEN processing an episode, THE Transcription_Pipeline SHALL complete all steps (download, transcribe, analyze) before starting the next episode
3. WHILE processing episodes, THE CLI SHALL display progress information indicating which episode is currently being processed
4. THE Transcription_Pipeline SHALL NOT process episodes in parallel

### Requirement 3: Error Handling and Continuation

**User Story:** As a podcast researcher, I want the batch process to continue even if one episode fails, so that I don't lose progress on successful transcriptions.

#### Acceptance Criteria

1. IF an episode fails during processing, THEN THE Transcription_Pipeline SHALL log the error and continue processing remaining episodes
2. WHEN an episode fails, THE CLI SHALL display an error message indicating which episode failed and why
3. WHEN batch processing completes, THE CLI SHALL display a summary showing successful and failed episodes
4. IF an INDEX value is out of range for the feed, THEN THE CLI SHALL log an error for that index and continue with remaining episodes
5. WHEN all episodes fail, THE CLI SHALL exit with a non-zero status code

### Requirement 4: Output Organization

**User Story:** As a podcast researcher, I want each transcribed episode to be saved in a separate file, so that I can easily locate and reference individual episode transcripts.

#### Acceptance Criteria

1. WHEN an episode is successfully transcribed, THE CLI SHALL save the output to a separate Markdown file
2. THE CLI SHALL use the existing output file naming convention for each episode
3. WHEN multiple episodes are processed, THE CLI SHALL NOT overwrite existing transcript files unless explicitly configured to do so
4. THE CLI SHALL maintain the existing YAML frontmatter format for each output file

### Requirement 5: Progress Reporting

**User Story:** As a podcast researcher, I want to see progress updates during batch processing, so that I know the tool is working and can estimate completion time.

#### Acceptance Criteria

1. WHEN batch processing starts, THE CLI SHALL display the total number of episodes to be processed
2. WHILE processing each episode, THE CLI SHALL display which episode number is currently being processed
3. WHEN an episode completes successfully, THE CLI SHALL display a success message with the output file path
4. WHEN batch processing completes, THE CLI SHALL display a summary with counts of successful and failed episodes
