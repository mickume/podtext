# Requirements Document

## Introduction

Podtext is a command-line tool that downloads podcast episodes from RSS feeds and transcribes them using MLX-Whisper (optimized for Apple Silicon). It uses Claude AI for post-processing including advertisement detection/removal and content analysis.

## Glossary

- **Podtext**: The command-line application being specified
- **Feed_URL**: A URL pointing to a podcast's RSS feed
- **Index_Number**: A numeric identifier assigned to episodes within a feed listing
- **MLX_Whisper**: Apple Silicon optimized implementation of OpenAI's Whisper speech recognition model
- **iTunes_API**: Apple's public API for searching podcast metadata
- **Claude_API**: Anthropic's API for AI-powered text analysis
- **Config_File**: TOML configuration file at `.podtext/config` (local) or `$HOME/.podtext/config` (global)
- **Advertisement_Block**: A section of transcribed content identified as promotional/advertising material
- **Frontmatter**: YAML metadata block at the beginning of a markdown file

## Requirements

### Requirement 1: Podcast Feed Discovery

**User Story:** As a user, I want to search for podcasts by keywords, so that I can find podcast feeds to transcribe.

#### Acceptance Criteria

1. WHEN a user provides search keywords, THE Podtext SHALL query the iTunes API and return matching podcasts
2. THE Podtext SHALL display podcast results with title and Feed_URL
3. THE Podtext SHALL limit results to N entries where N defaults to 10
4. WHEN a user specifies a custom result limit via command-line parameter, THE Podtext SHALL display that number of results instead of the default
5. IF the iTunes API returns an error, THEN THE Podtext SHALL display an error message and exit gracefully

### Requirement 2: Episode Discovery

**User Story:** As a user, I want to list recent episodes from a podcast feed, so that I can select specific episodes to transcribe.

#### Acceptance Criteria

1. WHEN a user provides a Feed_URL, THE Podtext SHALL retrieve and parse the RSS feed
2. THE Podtext SHALL display episodes with title, publication date, and Index_Number
3. THE Podtext SHALL limit results to the N most recent episodes where N defaults to 10
4. WHEN a user specifies a custom episode limit via command-line parameter, THE Podtext SHALL display that number of episodes instead of the default
5. IF the RSS feed is invalid or unreachable, THEN THE Podtext SHALL display an error message and exit gracefully

### Requirement 3: Media Download

**User Story:** As a user, I want to download podcast episode media files, so that they can be transcribed locally.

#### Acceptance Criteria

1. WHEN a user provides a Feed_URL and Index_Number, THE Podtext SHALL download the corresponding media file
2. THE Podtext SHALL store downloaded media in the configured directory (default: `.podtext/downloads/`)
3. WHERE temporary storage is configured, THE Podtext SHALL delete media files after transcription completes
4. IF the media file download fails, THEN THE Podtext SHALL display an error message and exit gracefully

### Requirement 4: Transcription Pipeline

**User Story:** As a user, I want podcast episodes transcribed using Whisper, so that I can read and analyze the content.

#### Acceptance Criteria

1. WHEN a media file is downloaded, THE Podtext SHALL transcribe it using MLX_Whisper
2. THE Podtext SHALL use the Whisper model specified in Config_File (default: 'base')
3. THE Podtext SHALL detect paragraph boundaries using Whisper's built-in segmentation
4. WHEN transcription completes, THE Podtext SHALL generate a markdown file with frontmatter metadata and transcribed text
5. THE Podtext SHALL include episode title, publication date, and keywords in the frontmatter

### Requirement 5: Language Verification

**User Story:** As a user, I want to be warned about non-English content, so that I can decide whether to proceed with transcription.

#### Acceptance Criteria

1. WHEN processing a media file, THE Podtext SHALL detect the audio language
2. IF the detected language is not English, THEN THE Podtext SHALL display a warning and continue transcription
3. WHERE the skip-language-check flag is provided, THE Podtext SHALL bypass language detection entirely

### Requirement 6: Advertisement Detection and Removal

**User Story:** As a user, I want advertisements removed from transcripts, so that I can focus on the actual content.

#### Acceptance Criteria

1. WHEN transcription completes, THE Podtext SHALL send the text to Claude_API for advertisement detection
2. WHEN Claude_API identifies an Advertisement_Block with high confidence, THE Podtext SHALL remove it from the output
3. THE Podtext SHALL insert "ADVERTISEMENT WAS REMOVED" marker where advertisements were removed
4. IF Claude_API is unavailable, THEN THE Podtext SHALL output the transcript without advertisement removal and display a warning

### Requirement 7: Content Analysis

**User Story:** As a user, I want AI-generated summaries and metadata, so that I can quickly understand episode content.

#### Acceptance Criteria

1. WHEN transcription completes, THE Podtext SHALL send the text to Claude_API for analysis
2. THE Podtext SHALL generate a summary of the transcription content
3. THE Podtext SHALL generate a list of topics covered (one sentence each)
4. THE Podtext SHALL generate a list of relevant keywords
5. THE Podtext SHALL detect and mark sponsor content (narrated ads) in the transcription
6. THE Podtext SHALL include all analysis results in the output markdown frontmatter

### Requirement 8: Configuration Management

**User Story:** As a user, I want configurable settings persisted in a file, so that I don't need to specify options repeatedly.

#### Acceptance Criteria

1. THE Podtext SHALL read configuration from `.podtext/config` (local) or `$HOME/.podtext/config` (global)
2. THE Podtext SHALL prioritize local configuration over global configuration
3. IF global Config_File does not exist, THEN THE Podtext SHALL create it on startup with default values
4. THE Podtext SHALL support configuring: Claude API key, media storage path, output location, Whisper model, and temporary storage option
5. WHEN environment variable `ANTHROPIC_API_KEY` is set, THE Podtext SHALL use it instead of the Config_File value

### Requirement 9: LLM Prompt Management

**User Story:** As a user, I want to customize LLM prompts without changing code, so that I can tune the AI behavior.

#### Acceptance Criteria

1. THE Podtext SHALL store all Claude_API prompts in an editable markdown file
2. THE Podtext SHALL load prompts from the markdown file at runtime
3. IF the prompts file is missing or malformed, THEN THE Podtext SHALL use built-in default prompts and display a warning

### Requirement 10: Installation and Environment

**User Story:** As a developer, I want standard Python packaging, so that the tool is easy to install and maintain.

#### Acceptance Criteria

1. THE Podtext SHALL be implemented using Python 3.13
2. THE Podtext SHALL be installable via pip or uv
3. THE Podtext SHALL use a virtual environment for dependency isolation
4. THE Podtext SHALL include extensive unit tests to verify requirements compliance
