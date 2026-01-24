"""Tests for CLI commands."""

from typer.testing import CliRunner

from podtext.cli.main import app

runner = CliRunner()


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_help(self) -> None:
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "podtext" in result.output
        assert "search" in result.output
        assert "episodes" in result.output
        assert "process" in result.output
        assert "reprocess" in result.output

    def test_version(self) -> None:
        """Test version command."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "podtext version" in result.output

    def test_search_help(self) -> None:
        """Test search command help."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search for podcasts" in result.output
        assert "--limit" in result.output

    def test_episodes_help(self) -> None:
        """Test episodes command help."""
        result = runner.invoke(app, ["episodes", "--help"])
        assert result.exit_code == 0
        assert "List episodes" in result.output
        assert "--limit" in result.output

    def test_process_help(self) -> None:
        """Test process command help."""
        result = runner.invoke(app, ["process", "--help"])
        assert result.exit_code == 0
        assert "Download, transcribe, and analyze" in result.output
        assert "--skip-language-check" in result.output
        assert "--keep-media" in result.output

    def test_reprocess_help(self) -> None:
        """Test reprocess command help."""
        result = runner.invoke(app, ["reprocess", "--help"])
        assert result.exit_code == 0
        assert "Re-process" in result.output
        assert "--podcast-title" in result.output
        assert "--episode-title" in result.output


class TestVerbosityOptions:
    """Tests for verbosity options."""

    def test_verbose_flag(self) -> None:
        """Test verbose flag parsing."""
        result = runner.invoke(app, ["-v", "--help"])
        assert result.exit_code == 0

    def test_quiet_flag(self) -> None:
        """Test quiet flag parsing."""
        result = runner.invoke(app, ["-q", "--help"])
        assert result.exit_code == 0

    def test_error_only_flag(self) -> None:
        """Test error-only flag parsing."""
        result = runner.invoke(app, ["--error-only", "--help"])
        assert result.exit_code == 0


class TestReprocessCommand:
    """Tests for reprocess command."""

    def test_reprocess_missing_file(self) -> None:
        """Test reprocess with non-existent file."""
        result = runner.invoke(app, ["reprocess", "/nonexistent/file.mp3"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()
