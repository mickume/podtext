# Requirements Document

## Introduction

This feature enhances the podcast transcription output by adding additional metadata to the YAML frontmatter. Specifically, it adds the podcast feed URL and the episode media file URL to provide better traceability and context for the transcribed content.

## Glossary

- **Frontmatter**: YAML metadata block at the beginning of a markdown file, delimited by `---` markers.
- **Feed_URL**: The RSS feed URL from which the podcast episode was discovered.
- **Media_URL**: The direct URL to the audio/video file that was transcribed.
- **EpisodeInfo**: A dataclass representing podcast episode metadata extracted from RSS feeds.
- **Output_Generator**: The component responsible for creating markdown files with frontmatter and transcribed content.

## Requirements

### Requirement 1: Include Feed URL in Frontmatter

**User Story:** As a user, I want the podcast feed URL included in the frontmatter, so that I can trace back to the original podcast source.

#### Acceptance Criteria

1. WHEN a transcription is generated, THE Output_Generator SHALL include a `feed_url` field in the YAML frontmatter
2. WHEN the feed URL is not available, THE Output_Generator SHALL omit the `feed_url` field from the frontmatter
3. THE `feed_url` field SHALL contain the complete RSS feed URL used to discover the episode

### Requirement 2: Include Media URL in Frontmatter

**User Story:** As a user, I want the episode media file URL included in the frontmatter, so that I can identify which audio file the transcription is based on.

#### Acceptance Criteria

1. WHEN a transcription is generated, THE Output_Generator SHALL include a `media_url` field in the YAML frontmatter
2. THE `media_url` field SHALL contain the direct URL to the audio/video file that was transcribed
3. THE EpisodeInfo dataclass SHALL provide the media URL to the Output_Generator

### Requirement 3: Maintain Backward Compatibility

**User Story:** As a user, I want existing frontmatter fields preserved, so that my existing workflows continue to work.

#### Acceptance Criteria

1. THE Output_Generator SHALL preserve all existing frontmatter fields: title, pub_date, podcast, summary, topics, keywords
2. WHEN new metadata fields are added, THE Output_Generator SHALL place them after the existing fields
3. THE Output_Generator SHALL maintain the same YAML formatting conventions for new fields

### Requirement 4: Data Flow for Feed URL

**User Story:** As a developer, I want the feed URL to flow through the system, so that it reaches the output generator.

#### Acceptance Criteria

1. THE EpisodeInfo dataclass SHALL include an optional `feed_url` field
2. WHEN parsing an RSS feed, THE RSS_Parser SHALL populate the `feed_url` field in each EpisodeInfo
3. THE Pipeline SHALL pass the feed URL through to the Output_Generator
