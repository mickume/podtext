# podtext Requirements Specification

This document specifies the requirements for podtext using the EARS (Easy Approach to Requirements Syntax) pattern.

## Document Information

- **Version**: 1.0
- **Status**: Draft
- **Source**: PRD v1.0

## EARS Pattern Reference

| Pattern | Template | Use Case |
|---------|----------|----------|
| Ubiquitous | The \<system\> shall \<action\> | Unconditional requirements |
| Event-driven | When \<trigger\>, the \<system\> shall \<action\> | Triggered behavior |
| Unwanted behavior | If \<condition\>, then the \<system\> shall \<action\> | Error/exception handling |
| State-driven | While \<state\>, the \<system\> shall \<action\> | State-dependent behavior |
| Optional feature | Where \<feature\>, the \<system\> shall \<action\> | Configurable features |

---

## 1. Podcast Discovery

### 1.1 Search Functionality

**REQ-1.1.1** [Ubiquitous]
The system shall search for podcasts using the public iTunes Search API.

**REQ-1.1.2** [Event-driven]
When the user provides a search term, the system shall query the iTunes API for podcasts matching by title, podcast name, author/publisher, or description keywords.

**REQ-1.1.3** [Ubiquitous]
The system shall display search results showing podcast title and feed URL.

**REQ-1.1.4** [Ubiquitous]
The system shall limit search results to N entries, where N defaults to 10.

**REQ-1.1.5** [Optional feature]
Where the user specifies a `--limit` parameter, the system shall override the default result count.

**REQ-1.1.6** [Ubiquitous]
The system shall query the iTunes API fresh for each search request (no caching).

### 1.2 Feed Validation

**REQ-1.2.1** [Unwanted behavior]
If the provided feed URL is invalid or unreachable, then the system shall display an error message and abort the operation.

**REQ-1.2.2** [Ubiquitous]
The system shall only support public (unauthenticated) podcast feeds.

---

## 2. Episode Discovery

### 2.1 Episode Listing

**REQ-2.1.1** [Event-driven]
When the user provides a feed URL, the system shall retrieve and parse the RSS feed data.

**REQ-2.1.2** [Ubiquitous]
The system shall extract the last N podcast episodes from the feed, where N defaults to 10.

**REQ-2.1.3** [Optional feature]
Where the user specifies a `--limit` parameter, the system shall override the default episode count.

**REQ-2.1.4** [Ubiquitous]
The system shall display episode results with title, publication date, and an index number.

**REQ-2.1.5** [Ubiquitous]
The system shall assign index numbers starting from 1 for the most recent episode.

---

## 3. Media Download

### 3.1 Download Behavior

**REQ-3.1.1** [Event-driven]
When the user provides a feed URL and index number, the system shall download the corresponding episode's media file.

**REQ-3.1.2** [Ubiquitous]
The system shall download media files to a configurable local directory, defaulting to the current working directory.

**REQ-3.1.3** [Event-driven]
When the media file is a video format, the system shall extract only the audio track.

**REQ-3.1.4** [Unwanted behavior]
If a download fails, then the system shall abort with an error message (no resume capability).

### 3.2 File Management

**REQ-3.2.1** [Ubiquitous]
The system shall delete downloaded media files after successful processing by default.

**REQ-3.2.2** [Optional feature]
Where the `keep_media` configuration option is enabled, the system shall retain downloaded media files after processing.

---

## 4. Transcription

### 4.1 Transcription Engine

**REQ-4.1.1** [Ubiquitous]
The system shall transcribe audio using MLX-Whisper, optimized for Apple M-series chips.

**REQ-4.1.2** [Ubiquitous]
The system shall use the "base" Whisper model by default.

**REQ-4.1.3** [Optional feature]
Where the `whisper_model` configuration option is set, the system shall use the specified model (tiny, base, small, medium, large).

### 4.2 Language Handling

**REQ-4.2.1** [Ubiquitous]
The system shall detect the language of the audio before transcribing.

**REQ-4.2.2** [Unwanted behavior]
If the detected language is not English, then the system shall log a warning and continue with transcription.

**REQ-4.2.3** [Optional feature]
Where the `--skip-language-check` flag is provided, the system shall skip language verification.

### 4.3 Text Segmentation

**REQ-4.3.1** [Ubiquitous]
The system shall segment transcribed text using Whisper's sentence/segment boundaries.

---

## 5. AI Analysis

### 5.1 Claude API Integration

**REQ-5.1.1** [Ubiquitous]
The system shall use the Claude API for transcript analysis.

**REQ-5.1.2** [Ubiquitous]
The system shall retrieve the Claude API key from the `ANTHROPIC_API_KEY` environment variable first.

**REQ-5.1.3** [State-driven]
While no environment variable is set, the system shall read the API key from the configuration file.

**REQ-5.1.4** [Ubiquitous]
The system shall use "claude-sonnet" (latest version) as the default model.

**REQ-5.1.5** [Optional feature]
Where the `claude_model` configuration option is set, the system shall use the specified model.

### 5.2 Analysis Features

**REQ-5.2.1** [Ubiquitous]
The system shall generate a summary of the transcription using the Claude API.

**REQ-5.2.2** [Ubiquitous]
The system shall generate a list of topics covered, each described in one sentence.

**REQ-5.2.3** [Ubiquitous]
The system shall generate a list of relevant keywords for labeling the transcription.

### 5.3 Advertising Detection

**REQ-5.3.1** [Ubiquitous]
The system shall detect advertising/sponsor content sections in the transcript using the Claude API.

**REQ-5.3.2** [Event-driven]
When advertising content is detected with confidence >= the configured threshold, the system shall remove the text and insert an "[ADVERTISING REMOVED]" marker.

**REQ-5.3.3** [Ubiquitous]
The system shall use a default confidence threshold of 90% for advertising removal.

**REQ-5.3.4** [Optional feature]
Where the `ad_confidence_threshold` configuration option is set, the system shall use the specified threshold.

---

## 6. Output Generation

### 6.1 Markdown Output

**REQ-6.1.1** [Ubiquitous]
The system shall create a markdown file containing episode metadata and the full transcription.

**REQ-6.1.2** [Ubiquitous]
The system shall include YAML frontmatter with title, publication date, and keywords.

**REQ-6.1.3** [Ubiquitous]
The system shall name output files using the pattern `{podcast-name}-{episode-title}.md`.

**REQ-6.1.4** [Ubiquitous]
The system shall truncate filenames to approximately 50 characters total.

**REQ-6.1.5** [Ubiquitous]
The system shall include the AI-generated summary, topics, and keywords in the output file.

---

## 7. Configuration

### 7.1 Configuration Files

**REQ-7.1.1** [Ubiquitous]
The system shall use TOML format for configuration files.

**REQ-7.1.2** [Ubiquitous]
The system shall look for configuration at `.podtext/config.toml` in the current directory first.

**REQ-7.1.3** [State-driven]
While no local configuration exists, the system shall use `$HOME/.podtext/config.toml`.

**REQ-7.1.4** [Event-driven]
When `$HOME/.podtext/config.toml` does not exist, the system shall create it with default values on startup.

### 7.2 LLM Prompt Configuration

**REQ-7.2.1** [Ubiquitous]
The system shall store all LLM prompts and metadata in a local markdown file.

**REQ-7.2.2** [Ubiquitous]
The system shall allow editing of LLM prompts without modifying source code.

---

## 8. Offline Mode

### 8.1 Re-processing

**REQ-8.1.1** [Event-driven]
When the user specifies a local media file, the system shall process it through the full transcription and analysis pipeline.

**REQ-8.1.2** [Ubiquitous]
The system shall support re-processing of previously downloaded media files.

---

## 9. Command Line Interface

### 9.1 Verbosity Control

**REQ-9.1.1** [Ubiquitous]
The system shall support four verbosity levels: quiet, error, normal, verbose.

**REQ-9.1.2** [Ubiquitous]
The system shall use "normal" verbosity by default.

**REQ-9.1.3** [State-driven]
While in quiet mode, the system shall produce no output except for critical failures.

**REQ-9.1.4** [State-driven]
While in error mode, the system shall display only error messages.

**REQ-9.1.5** [State-driven]
While in verbose mode, the system shall display detailed progress and debug information.

### 9.2 Error Handling

**REQ-9.2.1** [Unwanted behavior]
If an error occurs during processing, then the system shall fail fast and abort immediately.

**REQ-9.2.2** [Ubiquitous]
The system shall display meaningful error messages with actionable guidance.

---

## 10. Technical Requirements

### 10.1 Implementation

**REQ-10.1.1** [Ubiquitous]
The system shall be implemented in Python 3.13.

**REQ-10.1.2** [Ubiquitous]
The system shall be installable via pip or uv.

**REQ-10.1.3** [Ubiquitous]
The system shall use a virtual environment for dependency isolation.

### 10.2 Testing

**REQ-10.2.1** [Ubiquitous]
The system shall include extensive unit tests verifying all requirements.

**REQ-10.2.2** [Ubiquitous]
The system shall maintain test coverage for all core functionality.

---

## Requirements Traceability

| Requirement | PRD Section | Priority |
|-------------|-------------|----------|
| REQ-1.x | Discover podcast feed | Must Have |
| REQ-2.x | Discover podcast episodes | Must Have |
| REQ-3.x | Retrieve and process | Must Have |
| REQ-4.x | Transcription | Must Have |
| REQ-5.x | Claude API analysis | Must Have |
| REQ-6.x | Output generation | Must Have |
| REQ-7.x | Configuration | Must Have |
| REQ-8.x | Offline mode | Should Have |
| REQ-9.x | CLI | Must Have |
| REQ-10.x | Technical requirements | Must Have |
