# Requirements Document: Podtext

## Introduction

Podtext is a command-line tool that enables users to discover, download, and transcribe podcast episodes using Whisper (optimized for Apple Silicon), with additional AI-powered analysis and processing capabilities via Claude API. The tool provides podcast search, episode discovery, automatic transcription, and intelligent content analysis including summary generation and advertising detection.

## Glossary

- **Podtext**: The command-line application system
- **iTunes_API**: The public iTunes API endpoint used for podcast search
- **RSS_Feed**: XML feed containing podcast episode metadata and media URLs
- **FEED_URL**: The URL pointing to a podcast's RSS feed
- **INDEX_NUMBER**: Sequential identifier for episodes within a feed (1-based)
- **MLX_Whisper**: Apple Silicon-optimized Whisper transcription engine
- **Claude_API**: Anthropic's Claude AI API for text analysis
- **Media_File**: The audio file downloaded from a podcast episode
- **Transcription**: Text output from speech-to-audio conversion
- **Markdown_File**: Output file containing episode metadata and transcription
- **Config_File**: TOML configuration file storing user preferences and API keys
- **Ad_Block**: Segment of transcription identified as advertising content
- **Confidence_Threshold**: Percentage value determining ad removal certainty

## Requirements

### Requirement 1: Podcast Discovery

**User Story:** As a user, I want to search for podcasts by keywords, so that I can find relevant podcast feeds to subscribe to.

#### Acceptance Criteria

1. WHEN a user provides search keywords, THE Podtext SHALL query the iTunes_API with those keywords
2. WHEN iTunes_API returns results, THE Podtext SHALL extract podcast title and FEED_URL for each result
3. THE Podtext SHALL display the first N results where N defaults to 10
4. WHERE a user specifies a custom result limit, THE Podtext SHALL display that number of results instead
5. WHEN displaying results, THE Podtext SHALL show podcast title and FEED_URL for each entry

### Requirement 2: Episode Discovery

**User Story:** As a user, I want to view recent episodes from a podcast feed, so that I can select specific episodes to transcribe.

#### Acceptance Criteria

1. WHEN a user provides a FEED_URL, THE Podtext SHALL retrieve and parse the RSS_Feed from that URL
2. WHEN parsing the RSS_Feed, THE Podtext SHALL extract the last N episodes where N defaults to 10
3. WHERE a user specifies a custom episode limit, THE Podtext SHALL extract that number of episodes instead
4. WHEN displaying episodes, THE Podtext SHALL show episode title and publication date for each entry
5. THE Podtext SHALL assign an INDEX_NUMBER to each episode starting from 1

### Requirement 3: Episode Retrieval and Transcription

**User Story:** As a user, I want to download and transcribe podcast episodes, so that I can read and analyze podcast content in text form.

#### Acceptance Criteria

1. WHEN a user provides FEED_URL and INDEX_NUMBER, THE Podtext SHALL download the Media_File to local storage
2. WHEN the Media_File is downloaded, THE Podtext SHALL verify the language is English
3. WHERE language verification is disabled via flag, THE Podtext SHALL skip language verification
4. WHEN language is verified as English, THE Podtext SHALL transcribe using MLX_Whisper
5. WHEN transcribing, THE Podtext SHALL detect paragraph boundaries using Whisper's built-in function
6. WHEN transcription completes, THE Podtext SHALL create a Markdown_File with episode metadata as frontmatter
7. WHEN creating the Markdown_File, THE Podtext SHALL include the full Transcription text
8. WHEN processing completes, THE Podtext SHALL remove the Media_File by default
9. WHERE media file retention is configured, THE Podtext SHALL preserve the Media_File after processing

### Requirement 4: Apple Silicon Verification

**User Story:** As a user on non-Apple Silicon hardware, I want to be notified that the tool cannot run, so that I understand the platform requirements.

#### Acceptance Criteria

1. WHEN Podtext starts, THE Podtext SHALL detect the hardware platform
2. IF the platform is not Apple Silicon, THEN THE Podtext SHALL display a warning message
3. IF the platform is not Apple Silicon, THEN THE Podtext SHALL terminate execution

### Requirement 5: Claude API Integration

**User Story:** As a user, I want AI-powered analysis of transcriptions, so that I can quickly understand episode content and identify key topics.

#### Acceptance Criteria

1. WHEN a Transcription is complete, THE Podtext SHALL send the text to Claude_API
2. WHEN Claude_API processes the Transcription, THE Podtext SHALL request a summary
3. WHEN Claude_API processes the Transcription, THE Podtext SHALL request a list of topics with one sentence descriptions
4. WHEN Claude_API processes the Transcription, THE Podtext SHALL request a list of relevant keywords
5. WHEN Claude_API returns analysis results, THE Podtext SHALL include them in the Markdown_File

### Requirement 6: Advertising Detection and Removal

**User Story:** As a user, I want advertising content automatically detected and removed from transcriptions, so that I can focus on the core podcast content.

#### Acceptance Criteria

1. WHEN Claude_API processes the Transcription, THE Podtext SHALL request identification of Ad_Blocks
2. WHEN Claude_API identifies an Ad_Block with confidence above the Confidence_Threshold, THE Podtext SHALL remove that segment
3. WHEN an Ad_Block is removed, THE Podtext SHALL insert a visible marker at the removal location
4. WHERE ad removal is disabled via flag, THE Podtext SHALL skip advertising detection entirely
5. THE Podtext SHALL use a default Confidence_Threshold of 90 percent
6. WHERE a custom Confidence_Threshold is configured, THE Podtext SHALL use that value instead

### Requirement 7: Configuration Management

**User Story:** As a user, I want to configure tool behavior and API credentials, so that I can customize the tool to my preferences without command-line arguments.

#### Acceptance Criteria

1. WHEN Podtext starts, THE Podtext SHALL search for Config_File at .podtext/config in the current directory
2. IF Config_File is not found in current directory, THEN THE Podtext SHALL search at $HOME/.podtext/config
3. IF no Config_File exists, THEN THE Podtext SHALL create $HOME/.podtext/config with default values
4. THE Config_File SHALL store Claude API key
5. THE Config_File SHALL store Claude model identifier with default value 'claude-4.5-sonnet'
6. THE Config_File SHALL store file storage location with default as current directory
7. THE Config_File SHALL store media file retention preference with default as false
8. THE Config_File SHALL store Confidence_Threshold with default value of 90
9. WHERE Claude API key is set in environment variable, THE Podtext SHALL use that value instead of Config_File value
10. THE Config_File SHALL use TOML format

### Requirement 8: Prompt and Metadata Management

**User Story:** As a developer, I want LLM prompts and metadata stored in editable files, so that I can customize AI behavior without code changes.

#### Acceptance Criteria

1. THE Podtext SHALL store LLM prompts in local markdown files
2. THE Podtext SHALL store metadata templates in local markdown files
3. WHEN Podtext needs prompts or metadata, THE Podtext SHALL read from these markdown files
4. THE markdown files SHALL be editable by users with text editors

### Requirement 9: Command-Line Interface

**User Story:** As a user, I want a clear command-line interface with sub-commands, so that I can easily access different tool functions.

#### Acceptance Criteria

1. THE Podtext SHALL provide a single main command
2. THE Podtext SHALL provide sub-commands for podcast search, episode discovery, and transcription
3. WHEN a user invokes a sub-command, THE Podtext SHALL execute the corresponding functionality
4. THE Podtext SHALL accept configuration parameters via command-line flags
5. WHEN command-line flags conflict with Config_File values, THE Podtext SHALL prioritize command-line flags

### Requirement 10: File Organization

**User Story:** As a user, I want control over where files are stored, so that I can organize my transcriptions according to my workflow.

#### Acceptance Criteria

1. THE Podtext SHALL store Media_Files in a configurable location
2. THE Podtext SHALL store Markdown_Files in a configurable location
3. WHERE no storage location is configured, THE Podtext SHALL use a directory relative to the current working directory
4. THE Podtext SHALL create storage directories if they do not exist

### Requirement 11: Python Environment

**User Story:** As a developer, I want the tool to use modern Python with proper dependency management, so that installation and maintenance are straightforward.

#### Acceptance Criteria

1. THE Podtext SHALL require Python 3.13
2. THE Podtext SHALL use a virtual environment for all module dependencies
3. THE Podtext SHALL support installation via pip
4. THE Podtext SHALL support installation via uv

### Requirement 12: Testing Coverage

**User Story:** As a developer, I want comprehensive automated tests, so that I can ensure code quality and catch regressions.

#### Acceptance Criteria

1. THE Podtext SHALL include property-based tests for data transformation logic
2. THE Podtext SHALL include unit tests with mocked external dependencies for integration points
3. THE Podtext SHALL include unit tests for configuration parsing
4. THE Podtext SHALL include unit tests for CLI argument parsing
