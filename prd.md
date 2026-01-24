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

## Clarification

On Claude API key handling:
- read from environment variable (e.g., `ANTHROPIC_API_KEY`). Look for one in the TOML (default) if not defined in the environment

On Media file storage
- A configurable directory in the TOML config
- A default location like `.podtext/downloads/`, if nothing is defined
- Temporary storage that gets cleaned up after transcription. This can be controlled in the TOML file

On Output location
- Same as above - configurable vs default location.

On Whisper model selection
- configured in the TOML. Default='base'

On Error handling for non-English content
- Warning, but continue

On Advertising removal
- Remove them entirely from the output and insert a marker e.g. "ADVERTISEMENT WAS REMOVED"