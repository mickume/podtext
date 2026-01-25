# podtext

A command-line podcast transcription and analysis tool optimized for Apple Silicon.

Podtext downloads podcast episodes, transcribes them using MLX-Whisper, and generates markdown files with AI-powered analysis using Claude.

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.13+
- Anthropic API key (for Claude analysis features)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/podtext.git
cd podtext

# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

On first run, podtext creates a config file at `~/.podtext/config`. You can also create a local config at `.podtext/config` in your project directory (takes precedence).

Set your Anthropic API key via environment variable (recommended):

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Or add it to your config file:

```toml
[api]
anthropic_key = "your-key-here"

[storage]
media_dir = ".podtext/downloads/"
output_dir = ".podtext/output/"
temp_storage = false  # Set to true to delete media after transcription

[whisper]
model = "base"  # Options: tiny, base, small, medium, large
```

## Usage

### Search for podcasts

```bash
podtext search "podcast name or keywords"
podtext search "tech news" --limit 5
```

### List episodes from a feed

```bash
podtext episodes "https://example.com/feed.xml"
podtext episodes "https://example.com/feed.xml" --limit 20
```

### Transcribe an episode

```bash
# Use the episode index from the episodes list
podtext transcribe "https://example.com/feed.xml" 1
```

Output is saved as a markdown file in the configured output directory.

## License

MIT
