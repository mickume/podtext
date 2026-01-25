# Tech Stack

## Language & Runtime
- Python 3.13+
- macOS with Apple Silicon (M1/M2/M3) required

## Build System
- Hatchling (build backend)
- pip or uv for installation

## Core Dependencies
- `mlx-whisper` - Audio transcription (Apple Silicon optimized)
- `anthropic` - Claude AI API client
- `click` - CLI framework
- `httpx` - HTTP client
- `feedparser` - RSS parsing
- `tomli` - TOML config parsing

## Dev Dependencies
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `hypothesis` - Property-based testing
- `mypy` - Static type checking (strict mode)
- `ruff` - Linting and formatting

## Common Commands

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/podtext

# Type checking
mypy src/podtext

# Linting
ruff check src tests
ruff format src tests

# Run the CLI
podtext search "podcast name"
podtext episodes "https://feed.url"
podtext transcribe "https://feed.url" 1
```

## Configuration
- TOML format at `.podtext/config` (local) or `~/.podtext/config` (global)
- Environment variable `ANTHROPIC_API_KEY` takes precedence for API key
- Whisper models: tiny, base, small, medium, large
