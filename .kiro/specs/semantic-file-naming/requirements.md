# Requirements Document

## Introduction

This feature improves the output file naming and organization for transcribed podcast episodes. Currently, output files are named with a date prefix and truncated title in a flat directory structure. This feature introduces a hierarchical structure with podcast name subdirectories and cleansed, human-readable filenames with a maximum length of 30 characters.

## Glossary

- **Output_Path_Generator**: The component responsible for generating the full output path including directory structure and filename for transcribed episodes.
- **Path_Sanitizer**: A utility that cleanses strings to be safe for use in file system paths by removing or replacing invalid characters.
- **Podcast_Subdirectory**: A directory named after the podcast that contains all transcribed episodes for that podcast.
- **Safe_Filename**: A filename that contains only characters valid for file system paths and is within the maximum length limit.

## Requirements

### Requirement 1: Hierarchical Output Directory Structure

**User Story:** As a user, I want transcribed files organized in podcast-specific subdirectories, so that I can easily find and browse episodes by podcast.

#### Acceptance Criteria

1. WHEN an episode is transcribed, THE Output_Path_Generator SHALL create the output path in the format `<output-dir>/<podcast-name>/<episode-title>.md`
2. WHEN the podcast subdirectory does not exist, THE Output_Path_Generator SHALL create it automatically
3. WHEN multiple episodes from the same podcast are transcribed, THE Output_Path_Generator SHALL place them in the same podcast subdirectory

### Requirement 2: Path Component Sanitization

**User Story:** As a user, I want podcast names and episode titles to be cleansed for file system compatibility, so that files can be created on any operating system without errors.

#### Acceptance Criteria

1. THE Path_Sanitizer SHALL remove or replace characters that are invalid in file paths including: `/ \ : * ? " < > |`
2. THE Path_Sanitizer SHALL replace invalid characters with underscores
3. THE Path_Sanitizer SHALL preserve alphanumeric characters, spaces, hyphens, and underscores
4. THE Path_Sanitizer SHALL trim leading and trailing whitespace from the result
5. THE Path_Sanitizer SHALL collapse multiple consecutive underscores into a single underscore

### Requirement 3: Length Limitation

**User Story:** As a user, I want filenames and directory names to be reasonably short, so that paths remain readable and don't exceed file system limits.

#### Acceptance Criteria

1. THE Path_Sanitizer SHALL truncate path components to a maximum of 30 characters
2. WHEN truncating, THE Path_Sanitizer SHALL avoid cutting in the middle of a word when possible
3. THE Path_Sanitizer SHALL trim any trailing whitespace or underscores after truncation

### Requirement 4: Edge Case Handling

**User Story:** As a user, I want the system to handle unusual podcast names and episode titles gracefully, so that transcription never fails due to naming issues.

#### Acceptance Criteria

1. IF the podcast name is empty or contains only invalid characters, THEN THE Output_Path_Generator SHALL use "unknown-podcast" as the subdirectory name
2. IF the episode title is empty or contains only invalid characters, THEN THE Output_Path_Generator SHALL use "episode_<index>" as the filename (where index is the episode number)
3. IF the sanitized name would be empty after processing, THEN THE Path_Sanitizer SHALL return a fallback value
4. WHEN the podcast name is not provided to the pipeline, THE Output_Path_Generator SHALL use "unknown-podcast" as the subdirectory name

### Requirement 5: Backward Compatibility

**User Story:** As a user, I want to be able to specify a custom output path that overrides the new naming scheme, so that existing workflows are not broken.

#### Acceptance Criteria

1. WHEN a custom output_path is provided to run_pipeline, THE Output_Path_Generator SHALL use the custom path instead of generating one
2. THE Output_Path_Generator SHALL maintain the existing API signature for run_pipeline
