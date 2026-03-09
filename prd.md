# Product Requirements Document

**Version:** 1.0
**Date:** 2026-03-09
**Status:** Reverse-engineered from codebase

## 1. Product Overview

Podtext is a command-line tool that enables users to discover podcasts, download episodes, transcribe audio using hardware-accelerated speech recognition on Apple Silicon Macs, and generate enriched markdown documents containing the transcript along with AI-powered analysis (summaries, topics, keywords, and advertisement detection). It is designed for users who want searchable, readable text versions of podcast content with minimal manual effort.

## 2. Goals & Non-Goals

**Goals**

- Enable users to search for podcasts by keyword and discover RSS feed URLs
- Allow users to browse recent episodes from any podcast feed
- Produce high-quality audio transcriptions optimized for Apple Silicon hardware
- Enrich transcripts with AI-generated summaries, topics, keywords, and advertisement removal
- Output well-structured, human-readable markdown files with metadata
- Support batch processing of multiple episodes in a single command

**Non-Goals**

- Real-time or streaming transcription -- processing is offline and file-based
- Support for non-macOS or non-Apple-Silicon platforms -- the transcription engine requires Apple M-series chips
- A graphical user interface -- the product is CLI-only
- Audio or video editing -- the tool produces text output only
- Multi-language transcription -- the tool is optimized for English content and warns on non-English audio

## 3. User Personas

| Persona | Description | Primary Need |
|---|---|---|
| Podcast Researcher | An individual who consumes many podcasts and needs searchable, archivable text records of episodes | Quickly convert podcast episodes to structured, searchable text documents |
| Content Creator | A writer or journalist who references podcast discussions in their own work | Get accurate transcripts with topic summaries and keyword tags for easy reference |
| Casual Listener | A Mac user who occasionally wants a text version of a long episode to skim or share | Simple one-command transcription without complex setup |

## 4. User Workflows

**Workflow: Discover and Transcribe a Podcast Episode**

1. User searches for a podcast by keyword (e.g., `podtext search "artificial intelligence"`)
2. System displays a numbered list of matching podcasts with their titles and feed URLs
3. User copies a feed URL and lists its recent episodes (e.g., `podtext episodes "<feed_url>"`)
4. System displays a numbered list of episodes with titles and publication dates
5. User selects one or more episodes by index number to transcribe (e.g., `podtext transcribe "<feed_url>" 1 3 5`)
6. System downloads each episode's audio, transcribes it, runs AI analysis, and saves a markdown file
7. User receives a progress summary showing which episodes succeeded or failed
8. Outcome: The user has one markdown file per episode in the output directory, each containing metadata, a summary, show notes, and the full transcript

**Workflow: Batch Transcription**

1. User provides a feed URL and multiple episode indices in a single command
2. System processes episodes sequentially, showing progress (e.g., `[1/3] Processing episode 2...`)
3. If an episode fails, the system reports the error and continues with the remaining episodes
4. After all episodes are processed, a summary shows total successes and failures
5. Outcome: The user gets as many transcripts as possible from a single command, with clear reporting of any issues

**Workflow: Transcribe Non-English Content**

1. User initiates transcription of a podcast episode
2. System detects that the audio language is not English and displays a warning
3. Transcription proceeds despite the language mismatch
4. Alternatively, the user can bypass language detection entirely with `--skip-language-check`
5. Outcome: The user gets a transcript with a warning about potential quality issues for non-English content

**Failure Path: AI Analysis Unavailable**

1. User transcribes an episode but has no API key configured (or the AI service is unreachable)
2. System displays a warning that AI analysis will be skipped
3. System still produces a markdown file containing the raw transcript without summary, topics, keywords, or advertisement removal
4. Outcome: The user gets a usable transcript even when AI features are unavailable

## 5. Functional Requirements

**Capability Area: Podcast Discovery**

- [REQ-001] When the user provides search keywords, the system shall query the podcast directory and return matching podcasts with their titles and feed URLs.
- [REQ-002] The system shall display up to a configurable number of search results (default: 10).
- [REQ-003] If the podcast directory is unreachable or returns an error, the system shall display an error message and exit with a non-zero status.

**Capability Area: Episode Listing**

- [REQ-004] When the user provides a feed URL, the system shall retrieve the RSS feed and display recent episodes with index numbers, titles, and publication dates.
- [REQ-005] Episodes shall be sorted by publication date, most recent first, and assigned sequential index numbers starting from 1.
- [REQ-006] The system shall display up to a configurable number of episodes (default: 10).
- [REQ-007] If the feed URL is invalid, unreachable, or contains no episodes, the system shall display an error message and exit with a non-zero status.

**Capability Area: Transcription**

- [REQ-008] When the user provides a feed URL and one or more episode indices, the system shall download the audio, transcribe it, and produce a markdown output file.
- [REQ-009] The system shall support five transcription quality levels: tiny, base (default), small, medium, and large.
- [REQ-010] The system shall extract paragraph boundaries from the speech recognition engine's segmentation output to improve transcript readability.
- [REQ-011] If the audio file cannot be downloaded, the system shall display an error message and report the episode as failed.
- [REQ-012] If transcription fails, the system shall display an error message and report the episode as failed.

**Capability Area: Language Detection**

- [REQ-013] The system shall detect the language of the audio during transcription.
- [REQ-014] If the detected language is not English, the system shall display a warning but continue transcription.
- [REQ-015] Where the `--skip-language-check` flag is provided, the system shall bypass language detection entirely.

**Capability Area: AI-Powered Analysis**

- [REQ-016] When an API key is configured and the AI service is reachable, the system shall generate a content summary of the transcript.
- [REQ-017] The system shall extract a list of topics covered in the episode, each described in one sentence.
- [REQ-018] The system shall extract a list of relevant keywords (up to 15-20) to label the transcript.
- [REQ-019] The system shall detect advertisement sections in the transcript and replace them with a visible marker (`[ADVERTISEMENT WAS REMOVED]`).
- [REQ-020] Only advertisement detections with high confidence shall be applied to the transcript.
- [REQ-021] If the AI service is unavailable or returns an error, the system shall display a warning and produce the transcript without AI analysis (graceful degradation).
- [REQ-022] If the AI service returns a rate-limit error, the system shall report the error and stop processing.
- [REQ-023] The system shall automatically retry transient AI service errors (connection failures, server errors) up to 3 times with a 30-second delay between attempts.

**Capability Area: Batch Processing**

- [REQ-024] When multiple episode indices are provided, the system shall process them sequentially in the order specified.
- [REQ-025] Duplicate episode indices shall be removed before processing, preserving the order of first occurrence.
- [REQ-026] The system shall display a progress indicator showing the current episode number relative to the total (e.g., `[2/5]`).
- [REQ-027] If an individual episode fails during batch processing, the system shall continue processing the remaining episodes.
- [REQ-028] After batch processing completes, the system shall display a summary with counts of successful and failed episodes.
- [REQ-029] The system shall exit with status 0 if all episodes succeeded, or status 1 if any episode failed.

**Capability Area: Output Generation**

- [REQ-030] The system shall produce a markdown file containing YAML frontmatter and formatted transcript content.
- [REQ-031] The frontmatter shall include: episode title, publication date, podcast name, feed URL, media URL, topics, and keywords.
- [REQ-032] The main content shall include (when available): an AI-generated summary section, show notes converted from HTML to markdown, and the full transcript with paragraph formatting.
- [REQ-033] Output files shall be organized in a subdirectory named after the podcast, with filenames derived from the episode title.
- [REQ-034] Podcast names and episode titles used in file paths shall be sanitized (invalid characters replaced, length limited to 30 characters, truncated at word boundaries).
- [REQ-035] Show notes from the RSS feed shall be converted from HTML to markdown, preserving links, lists, headings, and text formatting.
- [REQ-036] If show notes exceed 50,000 characters, they shall be truncated with a notice.

## 6. Configuration & Input Specification

| Option | Description | Default | Valid Values |
|---|---|---|---|
| API Key | Authentication credential for the AI analysis service. Can be set via environment variable (takes precedence) or in the configuration file. | (empty) | Any valid API key string |
| Media Directory | Where downloaded audio files are stored | `.podtext/downloads/` | Any valid directory path |
| Output Directory | Where generated markdown files are saved | `.podtext/output/` | Any valid directory path |
| Temporary Storage | Whether to delete downloaded audio files after transcription | `false` | `true` or `false` |
| Transcription Model | Controls transcription speed vs. accuracy trade-off | `base` | `tiny`, `base`, `small`, `medium`, `large` |
| Search Result Limit | Maximum number of podcast search results to display (CLI flag `--limit` / `-n`) | 10 | Any positive integer |
| Episode Limit | Maximum number of episodes to list from a feed (CLI flag `--limit` / `-n`) | 10 | Any positive integer |
| Skip Language Check | Bypass audio language detection (CLI flag `--skip-language-check`) | `false` | Flag (present or absent) |

**Configuration File Locations:**

- Local configuration: `.podtext/config` in the current working directory (highest priority)
- Global configuration: `~/.podtext/config` in the user's home directory
- If neither exists, a local configuration file is auto-created with default values

**Prompt Customization:**

Users can customize the AI analysis prompts by editing a markdown file (`.podtext/prompts.md` locally or `~/.podtext/prompts.md` globally). The file contains four sections -- Advertisement Detection, Content Summary, Topic Extraction, and Keyword Extraction -- each with editable prompt text. If the file is missing or malformed, built-in defaults are used automatically. On first run, a default prompts file is created.

## 7. Output Specification

Each transcribed episode produces a single markdown file with the following structure:

```
---
title: "Episode Title"
pub_date: "2024-01-15"
podcast: "Podcast Name"
feed_url: "https://example.com/feed.xml"
media_url: "https://example.com/episode.mp3"
topics:
  - "Topic one: brief description"
  - "Topic two: brief description"
keywords:
  - keyword1
  - keyword2
---

## Summary

AI-generated multi-paragraph summary with section headlines...

## Show Notes

Converted markdown from the RSS feed's show notes...

## Transcription

Full transcribed text formatted into readable paragraphs...

[ADVERTISEMENT WAS REMOVED]

Continued transcript text...
```

**File naming:** `<output_dir>/<sanitized_podcast_name>/<sanitized_episode_title>.md`

When AI analysis is unavailable, the Summary section is omitted, and no topics, keywords, or advertisement markers are included. The transcript and show notes are always present.

## 8. Error Handling & User Feedback

| Scenario | User Experience |
|---|---|
| Invalid or unreachable podcast search service | Error message displayed; command exits with non-zero status |
| Invalid or unreachable RSS feed | Error message displayed; command exits with non-zero status |
| Audio download failure (timeout, HTTP error, network issue) | Error message displayed; episode marked as failed; batch continues |
| Transcription engine not installed | Error message indicating the missing dependency |
| Transcription failure | Error message displayed; episode marked as failed; batch continues |
| AI service API key not configured | Warning displayed; transcript produced without AI enrichment |
| AI service unreachable or returns errors | Warning displayed; transcript produced without AI enrichment |
| AI service rate limit exceeded | Warning displayed; processing stops |
| AI service transient error (connection/server) | Automatic retry up to 3 times with 30-second delays; warning shown per attempt |
| Non-English audio detected | Warning displayed; transcription continues |
| Invalid configuration file (malformed format) | Error message with details of the parsing issue |
| Invalid transcription model name in config | Error message listing valid model names |
| Partial download (interrupted) | Incomplete file is cleaned up automatically |

## 9. Constraints & Assumptions

**Constraints:**

- Requires macOS with Apple Silicon (M1/M2/M3) for the hardware-accelerated transcription engine
- Requires Python 3.13 or later
- An API key for the AI analysis service is required for summary, topic, keyword, and advertisement features; without it, only raw transcription is available
- Configuration files use TOML format
- The transcription engine downloads model files from a remote repository on first use

**Assumptions:**

- Podcast RSS feeds follow standard RSS/Atom conventions with enclosure elements for media files
- Audio files are directly downloadable via HTTP(S) without authentication
- The AI service is available and responsive for analysis features (the system degrades gracefully if not)
- Users have sufficient disk space for downloading audio files and storing transcripts
- The 5-minute download timeout is sufficient for typical podcast episode file sizes

## 10. Open Questions

| # | Question | Why it matters |
|---|---|---|
| 1 | Is there a maximum audio file size or duration that the transcription engine can handle reliably? | Users may encounter failures on very long episodes without understanding why |
| 2 | Should the tool support resuming interrupted downloads? | Large podcast files on slow connections may time out |
| 3 | How should the tool behave when an output file already exists for an episode? | Currently it silently overwrites; users may want skip or backup behavior |
| 4 | Should advertisement confidence threshold (0.8) be user-configurable? | Different users may want more or less aggressive ad removal |
| 5 | The existing PRD mentions creating `$HOME/.podtext/config` on startup, but the code only creates a local config and never auto-creates the global config. Which is intended? | Documentation and code disagree on first-run behavior |

## 11. Future Considerations

- The codebase includes show notes extraction and HTML-to-markdown conversion, suggesting interest in richer metadata beyond raw transcription
- The prompt customization system suggests potential for user-extensible analysis (custom AI queries beyond the four built-in ones)
- The architecture separates concerns cleanly (discovery, feed parsing, downloading, transcription, analysis, output), which would facilitate adding new output formats or alternative transcription engines
- Batch processing support is implemented, which could be extended to full-feed processing or scheduled/automated runs
