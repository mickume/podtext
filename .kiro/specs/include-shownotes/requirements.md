# Requirements Document

## Introduction

This feature adds podcast show notes to the transcription output. Many podcasts include extensive additional information in their RSS feed entries such as episode descriptions, links, guest information, and supplementary content. This feature extracts these show notes and appends them as a separate section at the end of the transcribed text, providing users with complete episode context.

## Glossary

- **Show_Notes**: Additional content from RSS feed entries including descriptions, summaries, and supplementary information about an episode.
- **EpisodeInfo**: A dataclass representing podcast episode metadata extracted from RSS feeds.
- **RSS_Parser**: The component responsible for parsing RSS feeds and extracting episode information.
- **Output_Generator**: The component responsible for creating markdown files with frontmatter and transcribed content.
- **HTML_Converter**: A utility that converts HTML content to markdown format for consistent output.

## Requirements

### Requirement 1: Extract Show Notes from RSS Feed

**User Story:** As a user, I want show notes extracted from podcast RSS feeds, so that I have access to all episode information.

#### Acceptance Criteria

1. WHEN parsing an RSS feed entry, THE RSS_Parser SHALL extract show notes from the `summary`, `content`, or `description` fields
2. WHEN multiple show notes fields are present, THE RSS_Parser SHALL prefer `content` over `summary` over `description`
3. WHEN no show notes fields are present, THE RSS_Parser SHALL set the show notes to an empty string
4. THE EpisodeInfo dataclass SHALL include a `show_notes` field to store the extracted content

### Requirement 2: Append Show Notes to Transcript Output

**User Story:** As a user, I want show notes appended to my transcript, so that I have complete episode context in one document.

#### Acceptance Criteria

1. WHEN generating markdown output, THE Output_Generator SHALL append show notes as a separate section after the transcribed content
2. THE show notes section SHALL be preceded by a markdown heading "## Show Notes"
3. WHEN show notes are empty or not available, THE Output_Generator SHALL omit the show notes section entirely
4. THE Output_Generator SHALL maintain a blank line between the transcribed content and the show notes section

### Requirement 3: Convert HTML Show Notes to Markdown

**User Story:** As a user, I want HTML show notes converted to readable markdown, so that the output is consistent and readable.

#### Acceptance Criteria

1. WHEN show notes contain HTML content, THE HTML_Converter SHALL convert it to markdown format
2. THE HTML_Converter SHALL preserve hyperlinks in markdown format `[text](url)`
3. THE HTML_Converter SHALL convert HTML lists to markdown list format
4. THE HTML_Converter SHALL convert HTML headings to markdown headings
5. THE HTML_Converter SHALL strip unsupported HTML tags while preserving text content
6. WHEN show notes contain plain text, THE HTML_Converter SHALL return the text unchanged

### Requirement 4: Handle Edge Cases Gracefully

**User Story:** As a user, I want the system to handle unusual show notes gracefully, so that transcription never fails due to show notes issues.

#### Acceptance Criteria

1. IF show notes contain malformed HTML, THEN THE HTML_Converter SHALL extract readable text content
2. IF show notes exceed 50,000 characters, THEN THE Output_Generator SHALL truncate and add a truncation notice
3. IF show notes extraction fails, THEN THE RSS_Parser SHALL log a warning and continue with empty show notes
4. THE system SHALL handle Unicode characters in show notes correctly
