# Product requiremnet

A command-line tool that downloads podcast episodes from RSS feeds and transcribes them using Whisper, optimized for Apple Silicon. Use Claude AI and its API for further processing and analysis of the transcribed podcast episode.

## Requirements
How podtext works:

1) discover podcast feed
- Given a search term (keywords or a sentence), use the public iTunes API endpoint to search for podcasts, by title, podcast name, author/publisher or any keywords in the podcast description.
- Present the results by podcast title and podcast FEED-URL. Only show the first N results, where by default N=10, but this can be controlled via a command line parameter.

2) discover podcast episodes
- Given a FEED-URL, retrieve the rss feed data and extract the last N podcast episodes, where by default N=10, but this can be controlled via a command line parameter.
- Present the results by episode title and publication date. Provide an INDEX-NUMBER that later allows to retrieve and process a specific podcast episode.

3) Retrieve, transcribe and process a podcast episode
- Given a FEED-URL and INDEX-NUMBER, download the media file (audio/video) to a local folder.
- Transcribes it using **MLX-Whisper** (optimized for Apple M-series chips).
- Creates a markdown file with some episode metadata (e.g. title, publication date, keywords etc) and the full transcription of the podcast episode.

Podcast transcription and post-processing
- Verify the language is English before transcribing. Tthis can be skipped with a flag if needed.
- Detect paragraphs in the transcription by using Whisper's built-in function for this.
- Create a markdown file with metadata as frontmatter and the transcribed text.
- Podcast episodes contain advertising at the beginning, end or in-between. Detect this advertising blocks, using Claude.ai API calls and remove this text from the transcript if confident that the section is really advertising.

Use Claude API to analyse the transcription in ordert to
- create a summary of the transcription
- create a list of topics covered, in one sentence
- create a list of relevant keywords to label the transcription
- try to detect "sponsor conten", i.e. narrated adds and mark them in the transciption

Requirements
- podtext is implemented with python 3.13. 
- Create a virtual env for all python modules need.
- The resulting tool and all its dependencies must be installed using pip or uv.
- All the metadata used to direct the LLM and the API calls to Claude should be in a local markdown file that can be edited without changing the implementation.
- podtext uses a TOML configuration file in the current directory (.podtext/config) or ($HOME/.podtext/config). If $HOME/.podtext/config does not exist, create it on startup.
- Use extensive unit test to verify that the implementation meets the requirements.

## Implementation planning
- Create a requirements document from this PRD. Use the EARS (Easy Approach to Requirements Syntax) pattern for the requirements document. Then create design document but don't go to overboard with details in the design document. After that create a detailled tasks document that allows to track the progress of the implementation.

## Clarifications

Discovery & Feed Handling
Podcast search caching: Should search results be cached locally, or should each search always hit the iTunes API fresh?
-> always search

Feed URL validation: What should happen if the user provides an invalid or unreachable feed URL? Should there be retry logic?
-> error message and abort

Authentication: Do you need to support authenticated/private podcast feeds, or only public ones?
-> only public ones

Media Handling
File cleanup: Should downloaded media files be automatically deleted after transcription, kept permanently, or should this be configurable?
-> clean-up after processing, configurable in the config file

Storage location: The PRD mentions "a local folder" for downloads. Should this be configurable, or is there a specific default location in mind (e.g., .podtext/downloads/)?
-> configurable in the config file, default relative to current directory

Video podcasts: For video podcasts, should the tool extract just the audio track, or is there any video-specific handling needed?
-> only extract the audio track

Resume/incremental: If a download fails partway, should there be resume capability?
-> abort, no resume capability

Transcription
Whisper model selection: MLX-Whisper supports multiple model sizes (tiny, base, small, medium, large). Should this be configurable? What's the default?
-> default='base', configurable in the config file

Non-English content: The PRD says to verify English before transcribing. What should happen if it's not English - abort with an error, or just warn and skip?
-> warning but continue

Paragraph detection: You mention "Whisper's built-in function" for paragraph detection. Note that Whisper provides word-level timestamps but not explicit paragraph segmentation. Are you referring to sentence/segment boundaries, or do you have a specific approach in mind?
-> sentence/segment boundaries

Claude AI Integration
API key management: How should the Claude API key be stored/configured? Environment variable, config file, or both?
-> environment variable first, then try to read from config file.

Model selection: Should the Claude model be configurable (e.g., claude-sonnet vs claude-opus)?
-> configurable, default=claude-sonnet

Advertising removal confidence: You mention "if confident that the section is really advertising." What confidence threshold or user confirmation mechanism should be used? Should the original text be preserved somewhere?
-> configurable, default=90%. remove the text in the transcript and insert a marker e.g. "ADVERTISING REMOVED"

Rate limiting/costs: Should there be any controls around API usage (e.g., confirmation before processing, cost estimation)?
-> no

Output & Configuration
Output file naming: What naming convention for the markdown output files? {podcast-name}-{episode-title}.md? Timestamps?
-> {podcast-name}-{episode-title}.md where podcast-name and episode-title are shortend

Frontmatter format: Any specific frontmatter fields beyond what's mentioned (title, publication date, keywords)?
-> no

Config precedence: If both .podtext/config (local) and $HOME/.podtext/config exist, which takes precedence? Should they merge?
-> local first, then in the user's home directory

General
Offline mode: Should any functionality work offline (e.g., re-analyzing already-downloaded transcripts)?
-> re-analyzing already-downloaded media files should be possible

Logging/verbosity: Should there be configurable verbosity levels for CLI output?
-> yes, the usual: verbose, normal, error

Error handling philosophy: For batch operations, should the tool fail fast on first error or continue processing remaining items?
-> fail fast

Filename shortening: You mention podcast-name and episode-title should be "shortened." What's the maximum length or truncation rule? (e.g., 50 characters each, or total filename length?)
-> total lenght ca 50 characters

Config file extension: Should it be .podtext/config.toml (explicit) or .podtext/config (no extension)?
-> config.toml

Offline re-analysis scope: You said re-analyzing already-downloaded media files should be possible. Does this mean:
-> start-over the process as if the media file was just downloaded

Verbosity levels: You mentioned "verbose, normal, error." Is "error" the quietest level (only errors shown), or should there also be a "quiet/silent" mode?
-> also have a "quiet mode" without any output.

Claude model default: You said claude-sonnet - should this be the latest version (currently claude-sonnet-4-20250514) or a specific version string?
-> "claude-sonnet" latest