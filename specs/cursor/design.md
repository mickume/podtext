# podtext Design Document

This document describes the technical design for podtext, a podcast transcription and analysis tool.

## Document Information

- **Version**: 1.0
- **Status**: Draft
- **Requirements**: specs/requirements.md

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│                      (podtext.cli)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Discovery│ │ Download │ │Transcribe│ │ Analysis │           │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Core Layer                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Config  │ │  Models  │ │  Output  │ │  Errors  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     External Services                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │ iTunes   │ │MLX-Whisper│ │ Claude   │                        │
│  │ API      │ │          │ │ API      │                        │
│  └──────────┘ └──────────┘ └──────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Layered architecture**: Clear separation between CLI, services, and core
2. **Single responsibility**: Each service handles one concern
3. **Fail fast**: Errors abort immediately with clear messages
4. **Configuration-driven**: Behavior customizable without code changes
5. **Testability**: All services are independently testable

---

## 2. Project Structure

```
podtext/
├── pyproject.toml
├── README.md
├── prompts/
│   └── analysis.md          # LLM prompts (editable)
├── src/
│   └── podtext/
│       ├── __init__.py
│       ├── __main__.py       # Entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py       # CLI commands
│       │   └── output.py     # CLI output formatting
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py     # Configuration management
│       │   ├── errors.py     # Custom exceptions
│       │   └── models.py     # Data models
│       ├── services/
│       │   ├── __init__.py
│       │   ├── discovery.py  # iTunes + RSS services
│       │   ├── download.py   # Media download
│       │   ├── transcribe.py # MLX-Whisper transcription
│       │   ├── analysis.py   # Claude API analysis
│       │   └── output.py     # Markdown generation
│       └── utils/
│           ├── __init__.py
│           ├── audio.py      # Audio extraction
│           └── text.py       # Text utilities
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_discovery.py
    ├── test_download.py
    ├── test_transcribe.py
    ├── test_analysis.py
    └── test_output.py
```

---

## 3. Data Models

### 3.1 Podcast

```python
@dataclass
class Podcast:
    """Represents a podcast from iTunes search."""
    title: str
    feed_url: str
    author: str | None = None
    description: str | None = None
    artwork_url: str | None = None
```

### 3.2 Episode

```python
@dataclass
class Episode:
    """Represents a podcast episode from RSS feed."""
    index: int
    title: str
    published: datetime
    media_url: str
    duration: int | None = None  # seconds
    description: str | None = None
```

### 3.3 Transcript

```python
@dataclass
class Segment:
    """A segment of transcribed text."""
    text: str
    start: float  # seconds
    end: float    # seconds

@dataclass
class Transcript:
    """Complete transcription result."""
    segments: list[Segment]
    language: str
    duration: float
    
    @property
    def full_text(self) -> str:
        """Return concatenated text from all segments."""
        return " ".join(s.text for s in self.segments)
```

### 3.4 Analysis

```python
@dataclass
class AdvertisingBlock:
    """Detected advertising section."""
    start_index: int  # segment index
    end_index: int
    confidence: float

@dataclass
class Analysis:
    """Claude API analysis result."""
    summary: str
    topics: list[str]
    keywords: list[str]
    advertising_blocks: list[AdvertisingBlock]
```

### 3.5 Output

```python
@dataclass
class EpisodeOutput:
    """Final output combining all data."""
    podcast_title: str
    episode: Episode
    transcript: Transcript
    analysis: Analysis
```

---

## 4. Service Interfaces

### 4.1 Discovery Service

```python
class DiscoveryService:
    """Handles podcast and episode discovery."""
    
    def search_podcasts(self, query: str, limit: int = 10) -> list[Podcast]:
        """Search iTunes API for podcasts."""
        ...
    
    def get_episodes(self, feed_url: str, limit: int = 10) -> list[Episode]:
        """Fetch episodes from RSS feed."""
        ...
```

### 4.2 Download Service

```python
class DownloadService:
    """Handles media file downloads."""
    
    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
    
    def download(self, episode: Episode) -> Path:
        """Download episode media, return local path."""
        ...
    
    def extract_audio(self, media_path: Path) -> Path:
        """Extract audio from video file if needed."""
        ...
    
    def cleanup(self, path: Path) -> None:
        """Remove downloaded file."""
        ...
```

### 4.3 Transcription Service

```python
class TranscriptionService:
    """Handles audio transcription with MLX-Whisper."""
    
    def __init__(self, model: str = "base"):
        self.model = model
    
    def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe audio file."""
        ...
    
    def detect_language(self, audio_path: Path) -> str:
        """Detect audio language."""
        ...
```

### 4.4 Analysis Service

```python
class AnalysisService:
    """Handles Claude API analysis."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def analyze(self, transcript: Transcript) -> Analysis:
        """Perform full analysis on transcript."""
        ...
    
    def detect_advertising(
        self, 
        transcript: Transcript, 
        threshold: float = 0.9
    ) -> list[AdvertisingBlock]:
        """Detect advertising sections."""
        ...
```

### 4.5 Output Service

```python
class OutputService:
    """Handles markdown file generation."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def generate(self, output: EpisodeOutput) -> Path:
        """Generate markdown file, return path."""
        ...
    
    def generate_filename(
        self, 
        podcast_title: str, 
        episode_title: str, 
        max_length: int = 50
    ) -> str:
        """Generate truncated filename."""
        ...
```

---

## 5. Configuration

### 5.1 Configuration Schema

```toml
# .podtext/config.toml

[general]
download_dir = "./downloads"      # Relative to cwd or absolute
output_dir = "./transcripts"      # Where to save markdown files
keep_media = false                # Keep media files after processing
verbosity = "normal"              # quiet, error, normal, verbose

[transcription]
whisper_model = "base"            # tiny, base, small, medium, large
skip_language_check = false       # Skip English verification

[analysis]
claude_model = "claude-sonnet-4-20250514"
ad_confidence_threshold = 0.9     # 0.0 to 1.0
# api_key = "sk-..."              # Optional, prefer env var

[defaults]
search_limit = 10                 # Default podcast search results
episode_limit = 10                # Default episode list size
```

### 5.2 Configuration Loading

```python
class Config:
    """Configuration manager with precedence handling."""
    
    @classmethod
    def load(cls) -> "Config":
        """
        Load config with precedence:
        1. .podtext/config.toml (local)
        2. $HOME/.podtext/config.toml (user)
        3. Built-in defaults
        """
        ...
    
    @classmethod
    def ensure_user_config(cls) -> Path:
        """Create $HOME/.podtext/config.toml if missing."""
        ...
```

### 5.3 API Key Resolution

```python
def get_api_key(config: Config) -> str:
    """
    Get Claude API key with precedence:
    1. ANTHROPIC_API_KEY environment variable
    2. config.analysis.api_key
    3. Raise ConfigError
    """
    ...
```

---

## 6. CLI Design

### 6.1 Command Structure

```
podtext <command> [options]

Commands:
  search    Search for podcasts
  episodes  List episodes from a feed
  process   Download, transcribe, and analyze an episode
  reprocess Re-process a local media file

Global Options:
  -v, --verbose    Verbose output
  -q, --quiet      Suppress all output
  --error-only     Show only errors
  --config PATH    Use specific config file
```

### 6.2 Command Details

**Search command:**
```
podtext search <query> [--limit N]

Examples:
  podtext search "software engineering"
  podtext search "The Tim Ferriss Show" --limit 5
```

**Episodes command:**
```
podtext episodes <feed-url> [--limit N]

Examples:
  podtext episodes "https://example.com/feed.xml"
  podtext episodes "https://example.com/feed.xml" --limit 20
```

**Process command:**
```
podtext process <feed-url> <index> [options]

Options:
  --skip-language-check    Skip English language verification
  --keep-media             Don't delete media after processing
  --output-dir PATH        Override output directory

Examples:
  podtext process "https://example.com/feed.xml" 1
  podtext process "https://example.com/feed.xml" 3 --keep-media
```

**Reprocess command:**
```
podtext reprocess <media-file> [options]

Options:
  --podcast-title TEXT     Podcast title for output
  --episode-title TEXT     Episode title for output
  
Examples:
  podtext reprocess ./downloads/episode.mp3 --podcast-title "My Podcast"
```

### 6.3 Output Formatting

| Verbosity | Shows |
|-----------|-------|
| quiet | Nothing (exit codes only) |
| error | Error messages only |
| normal | Progress indicators, results, warnings |
| verbose | Debug info, API calls, timing |

---

## 7. LLM Prompt Management

### 7.1 Prompt File Structure

```markdown
<!-- prompts/analysis.md -->

# Analysis Prompts

## Summary Prompt

Generate a concise summary of this podcast transcript in 2-3 paragraphs.
Focus on the main themes and key takeaways.

---

## Topics Prompt

List the main topics covered in this transcript.
Each topic should be described in one sentence.
Return as a numbered list.

---

## Keywords Prompt

Extract 5-10 relevant keywords that describe this content.
Return as a comma-separated list.

---

## Advertising Detection Prompt

Analyze this transcript section and determine if it is advertising content.
Advertising includes: sponsor reads, product promotions, discount codes, 
"this episode is brought to you by" segments.

Return a JSON object:
{
  "is_advertising": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}
```

### 7.2 Prompt Loading

```python
class PromptManager:
    """Load and manage LLM prompts from markdown file."""
    
    def __init__(self, prompt_file: Path):
        self.prompts = self._parse_prompts(prompt_file)
    
    def get(self, name: str) -> str:
        """Get prompt by section name."""
        return self.prompts[name]
```

---

## 8. Error Handling

### 8.1 Exception Hierarchy

```python
class PodtextError(Exception):
    """Base exception for all podtext errors."""
    pass

class ConfigError(PodtextError):
    """Configuration-related errors."""
    pass

class DiscoveryError(PodtextError):
    """Podcast/episode discovery errors."""
    pass

class DownloadError(PodtextError):
    """Media download errors."""
    pass

class TranscriptionError(PodtextError):
    """Transcription errors."""
    pass

class AnalysisError(PodtextError):
    """Claude API errors."""
    pass

class OutputError(PodtextError):
    """File output errors."""
    pass
```

### 8.2 Error Messages

All errors include:
- Clear description of what went wrong
- Actionable guidance when possible
- No stack traces in normal mode (verbose only)

---

## 9. External Dependencies

### 9.1 Python Packages

| Package | Purpose |
|---------|---------|
| `mlx-whisper` | Apple Silicon optimized transcription |
| `anthropic` | Claude API client |
| `httpx` | HTTP client for API calls |
| `feedparser` | RSS feed parsing |
| `typer` | CLI framework |
| `rich` | Terminal formatting |
| `pydantic` | Configuration validation |
| `ffmpeg-python` | Audio extraction from video |
| `tomli` / `tomllib` | TOML parsing |

### 9.2 External Tools

| Tool | Purpose |
|------|---------|
| `ffmpeg` | Audio extraction (must be installed separately) |

---

## 10. Key Workflows

### 10.1 Full Processing Pipeline

```
1. User: podtext process <feed-url> <index>
2. Load configuration
3. Fetch RSS feed → get Episode
4. Download media file
5. Extract audio (if video)
6. Detect language → warn if not English
7. Transcribe with MLX-Whisper
8. Send to Claude API:
   a. Generate summary
   b. Extract topics
   c. Extract keywords
   d. Detect advertising
9. Remove advertising sections (if confident)
10. Generate markdown output
11. Cleanup media (unless keep_media)
12. Display result path
```

### 10.2 Reprocessing Pipeline

```
1. User: podtext reprocess <media-file>
2. Load configuration
3. Verify file exists
4. Extract audio (if video)
5. Continue from step 6 of full pipeline
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

- Each service tested independently
- Mock external APIs (iTunes, Claude)
- Test configuration loading and precedence
- Test error handling paths

### 11.2 Integration Tests

- End-to-end workflow with mocked APIs
- Configuration file handling
- CLI command parsing

### 11.3 Test Fixtures

- Sample RSS feed XML
- Sample transcription segments
- Sample Claude API responses
