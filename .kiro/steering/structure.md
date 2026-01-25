# Project Structure

```
podtext/
├── src/podtext/           # Main package (src layout)
│   ├── cli/               # CLI commands (Click)
│   │   └── main.py        # Entry point, command definitions
│   ├── core/              # Core business logic
│   │   ├── config.py      # TOML config loading, validation
│   │   ├── output.py      # Markdown generation
│   │   ├── pipeline.py    # Orchestrates download→transcribe→analyze
│   │   ├── processor.py   # Text processing utilities
│   │   └── prompts.py     # Claude prompt loading
│   └── services/          # External service integrations
│       ├── claude.py      # Claude API client
│       ├── downloader.py  # Media file downloading
│       ├── itunes.py      # iTunes podcast search API
│       ├── rss.py         # RSS feed parsing
│       └── transcriber.py # MLX-Whisper transcription
├── tests/                 # Test files (pytest)
│   ├── test_*.py          # Unit tests
│   └── test_*_properties.py  # Property-based tests (Hypothesis)
├── .podtext/              # Local config and data
│   ├── config             # Local TOML configuration
│   ├── downloads/         # Downloaded media files
│   ├── output/            # Generated transcripts
│   └── prompts.md         # Customizable Claude prompts
└── pyproject.toml         # Project metadata and tool config
```

## Architecture Patterns

- **Layered architecture**: CLI → Core → Services
- **Dataclasses** for structured data (Config, Results, etc.)
- **Custom exceptions** per module (e.g., `ConfigError`, `TranscriptionError`)
- **Graceful degradation**: Claude API failures don't block transcription
- **Context managers** for resource cleanup (temp file handling)

## Code Conventions

- Type hints on all functions (mypy strict mode)
- Docstrings with Args/Returns/Raises sections
- Requirement traceability via `Validates: Requirements X.Y` comments
- Tests mirror source structure with `test_` prefix
- Property-based tests use `_properties.py` suffix

## Code Repo

GitHub repo url: https://github.com/mickume/podtext