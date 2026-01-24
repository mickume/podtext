# Requirements Specification: podtext

This document specifies the requirements for podtext using the EARS (Easy Approach to Requirements Syntax) pattern.

## 1. General System Requirements

### 1.1 Platform & Environment

| ID | Requirement |
|----|-------------|
| GEN-01 | The system shall be implemented in Python 3.13. |
| GEN-02 | The system shall be installable via pip or uv. |
| GEN-03 | The system shall create a virtual environment for all required Python modules. |
| GEN-04 | The system shall be optimized for Apple Silicon (M-series chips). |

### 1.2 Configuration

| ID | Requirement |
|----|-------------|
| CFG-01 | When podtext starts, the system shall look for a configuration file at `.podtext/config.toml` in the current directory. |
| CFG-02 | If no local configuration file exists, the system shall look for `$HOME/.podtext/config.toml`. |
| CFG-03 | If `$HOME/.podtext/config.toml` does not exist, the system shall create it with default values on startup. |
| CFG-04 | The system shall store LLM prompts in `.podtext/ANALYSIS.md`, creating it with defaults if it does not exist. |
| CFG-05 | The system shall allow configuration of: output directory, media cleanup behavior, Whisper model size, Claude API model, result limits, and API keys. |

## 2. CLI Requirements

### 2.1 Command Structure

| ID | Requirement |
|----|-------------|
| CLI-01 | The system shall provide a `search` subcommand for podcast discovery. |
| CLI-02 | The system shall provide an `episodes` subcommand for listing podcast episodes. |
| CLI-03 | The system shall provide a `transcribe` subcommand for downloading and processing episodes. |

### 2.2 Search Command

| ID | Requirement |
|----|-------------|
| CLI-10 | When the user invokes `podtext search <term>`, the system shall query the iTunes API for matching podcasts. |
| CLI-11 | The system shall search by title, podcast name, author/publisher, and description keywords. |
| CLI-12 | The system shall display results showing podcast title and feed URL. |
| CLI-13 | The system shall display the first N results, where N defaults to 10. |
| CLI-14 | The system shall accept a command-line parameter to override the default result limit. |

### 2.3 Episodes Command

| ID | Requirement |
|----|-------------|
| CLI-20 | When the user invokes `podtext episodes <feed-url>`, the system shall retrieve the RSS feed. |
| CLI-21 | The system shall extract and display the last N episodes, where N defaults to 10. |
| CLI-22 | The system shall display episode title, publication date, and an INDEX-NUMBER for each episode. |
| CLI-23 | The INDEX-NUMBER shall be session-relative (1 to N for the displayed list). |
| CLI-24 | The system shall accept a command-line parameter to override the default episode limit. |

### 2.4 Transcribe Command

| ID | Requirement |
|----|-------------|
| CLI-30 | When the user invokes `podtext transcribe <feed-url> <index>`, the system shall download the specified episode's media file. |
| CLI-31 | The system shall transcribe the media file using MLX-Whisper. |
| CLI-32 | The system shall create a markdown file with episode metadata and transcription. |
| CLI-33 | The system shall save output to `<output-dir>/<podcast-name>/<episode-title>.md`. |

## 3. Transcription Requirements

### 3.1 Language Handling

| ID | Requirement |
|----|-------------|
| TRX-01 | The system shall verify the episode language is English before transcribing. |
| TRX-02 | If the language is not English, the system shall display a warning and continue transcription. |
| TRX-03 | The system shall accept a `--skip-language-check` flag to bypass language verification. |

### 3.2 Whisper Processing

| ID | Requirement |
|----|-------------|
| TRX-10 | The system shall use MLX-Whisper for transcription. |
| TRX-11 | The system shall use the 'base' Whisper model by default. |
| TRX-12 | The system shall allow the Whisper model size to be configured (tiny/base/small/medium/large). |
| TRX-13 | The system shall detect paragraph boundaries using Whisper's built-in segmentation. |

### 3.3 Media File Handling

| ID | Requirement |
|----|-------------|
| TRX-20 | The system shall download audio or video media files to a local folder. |
| TRX-21 | The system shall delete downloaded media files after successful transcription by default. |
| TRX-22 | The system shall allow media cleanup behavior to be configured (keep/delete). |

## 4. Output Requirements

### 4.1 Markdown Generation

| ID | Requirement |
|----|-------------|
| OUT-01 | The system shall create a markdown file for each transcribed episode. |
| OUT-02 | The system shall include YAML frontmatter with episode metadata. |
| OUT-03 | The frontmatter shall include: title, publication date, podcast name, and keywords. |
| OUT-04 | The system shall include the full transcription text after the frontmatter. |
| OUT-05 | The system shall organize output files as `<podcast-name>/<episode-title>.md`. |

## 5. Claude AI Analysis Requirements

### 5.1 API Configuration

| ID | Requirement |
|----|-------------|
| AI-01 | The system shall use the Claude API for transcript analysis. |
| AI-02 | The system shall use `claude-sonnet-4-20250514` as the default model. |
| AI-03 | The system shall allow the Claude model to be configured. |
| AI-04 | The system shall read LLM prompts from `.podtext/ANALYSIS.md`. |

### 5.2 Content Analysis

| ID | Requirement |
|----|-------------|
| AI-10 | The system shall generate a summary of the transcription. |
| AI-11 | The system shall generate a list of topics covered (one sentence each). |
| AI-12 | The system shall generate relevant keywords for labeling. |
| AI-13 | The system shall include the summary, topics, and keywords in the output frontmatter. |

### 5.3 Advertising Detection

| ID | Requirement |
|----|-------------|
| AI-20 | The system shall use Claude API to detect advertising blocks in the transcript. |
| AI-21 | The system shall detect sponsor content (narrated ads) within the episode. |
| AI-22 | When advertising is detected with high confidence, the system shall remove the advertising text. |
| AI-23 | The system shall replace removed advertising with the marker text "[ADVERTISING REMOVED]". |

## 6. Quality Requirements

### 6.1 Testing

| ID | Requirement |
|----|-------------|
| QA-01 | The system shall include extensive unit tests. |
| QA-02 | Unit tests shall verify all functional requirements are met. |

### 6.2 Maintainability

| ID | Requirement |
|----|-------------|
| QA-10 | The system shall allow LLM prompts to be edited without changing implementation code. |
| QA-11 | The system shall externalize all Claude API prompts to `.podtext/ANALYSIS.md`. |

## Appendix: Configuration Defaults

| Setting | Default Value |
|---------|---------------|
| `output_dir` | `./transcripts` |
| `cleanup_media` | `true` |
| `whisper_model` | `base` |
| `claude_model` | `claude-sonnet-4-20250514` |
| `search_limit` | `10` |
| `episode_limit` | `10` |
