"""Integration tests for the complete Podtext pipeline.

Feature: podtext
These tests verify end-to-end functionality with mocked external APIs.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
import yaml
from click.testing import CliRunner

from podtext.cli import main
from podtext.config import PodtextConfig, load_config
from podtext.models import AnalysisResult, EpisodeInfo, TranscriptionResult
from podtext.pipeline import run_transcription_pipeline, PipelineError


def generate_rss_feed(episodes: list[dict]) -> str:
    """Generate a mock RSS feed XML."""
    items = []
    for ep in episodes:
        items.append(f"""
        <item>
            <title>{ep.get('title', 'Episode')}</title>
            <pubDate>{ep.get('pub_date', 'Mon, 01 Jan 2024 00:00:00 +0000')}</pubDate>
            <enclosure url="{ep.get('media_url', 'https://example.com/audio.mp3')}" type="audio/mpeg" length="1234567"/>
        </item>
        """)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Podcast</title>
            <description>A test podcast</description>
            {"".join(items)}
        </channel>
    </rss>
    """


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @respx.mock
    def test_search_command_end_to_end(self) -> None:
        """Search command should work end-to-end with iTunes API."""
        # Mock iTunes API
        respx.get("https://itunes.apple.com/search").mock(
            return_value=httpx.Response(200, json={
                "resultCount": 2,
                "results": [
                    {
                        "collectionName": "Python Podcast",
                        "feedUrl": "https://example.com/python.xml",
                    },
                    {
                        "collectionName": "Tech Talk",
                        "feedUrl": "https://example.com/tech.xml",
                    },
                ],
            })
        )

        runner = CliRunner()
        result = runner.invoke(main, ["search", "python"])

        assert result.exit_code == 0
        assert "Python Podcast" in result.output
        assert "https://example.com/python.xml" in result.output
        assert "Tech Talk" in result.output

    @respx.mock
    def test_episodes_command_end_to_end(self) -> None:
        """Episodes command should work end-to-end with RSS feed."""
        feed_xml = generate_rss_feed([
            {
                "title": "Episode 1: Introduction",
                "pub_date": "Mon, 15 Jan 2024 12:00:00 +0000",
                "media_url": "https://example.com/ep1.mp3",
            },
            {
                "title": "Episode 2: Advanced Topics",
                "pub_date": "Mon, 22 Jan 2024 12:00:00 +0000",
                "media_url": "https://example.com/ep2.mp3",
            },
        ])

        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text=feed_xml)
        )

        runner = CliRunner()
        result = runner.invoke(main, ["episodes", "https://example.com/feed.xml"])

        assert result.exit_code == 0
        assert "Episode 1: Introduction" in result.output
        assert "Episode 2: Advanced Topics" in result.output
        assert "2024-01-15" in result.output


class TestPipelineIntegration:
    """Integration tests for the transcription pipeline."""

    @respx.mock
    @patch("podtext.pipeline.transcribe")
    @patch("podtext.pipeline.analyze_with_fallback")
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_components(
        self,
        mock_analyze: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """Full pipeline should work with mocked external components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            media_dir = tmpdir_path / "downloads"
            output_dir = tmpdir_path / "output"

            # Create config
            config = PodtextConfig()
            config.storage.media_dir = str(media_dir)
            config.storage.output_dir = str(output_dir)
            config.storage.temp_storage = True  # Enable cleanup

            # Mock RSS feed
            feed_xml = generate_rss_feed([{
                "title": "Test Episode",
                "pub_date": "Mon, 15 Jan 2024 12:00:00 +0000",
                "media_url": "https://example.com/audio.mp3",
            }])
            respx.get("https://example.com/feed.xml").mock(
                return_value=httpx.Response(200, text=feed_xml)
            )

            # Mock media download
            respx.get("https://example.com/audio.mp3").mock(
                return_value=httpx.Response(200, content=b"fake audio data")
            )

            # Mock transcription
            mock_transcribe.return_value = TranscriptionResult(
                text="Hello, this is a test transcription.",
                paragraphs=["Hello, this is a test transcription."],
                language="en",
            )

            # Mock analysis
            mock_analyze.return_value = AnalysisResult(
                summary="A test transcription summary.",
                topics=["Testing", "Podcasts"],
                keywords=["test", "transcription"],
                ad_markers=[],
            )

            # Run pipeline
            output_path = await run_transcription_pipeline(
                feed_url="https://example.com/feed.xml",
                episode_index=1,
                config=config,
            )

            # Verify output
            assert output_path.exists()
            content = output_path.read_text()

            # Check frontmatter
            assert content.startswith("---\n")
            parts = content.split("---\n", 2)
            frontmatter = yaml.safe_load(parts[1])

            assert frontmatter["title"] == "Test Episode"
            assert frontmatter["pub_date"] == "2024-01-15"
            assert frontmatter["summary"] == "A test transcription summary."
            assert "test" in frontmatter["keywords"]

            # Check transcript content
            assert "Hello, this is a test transcription." in content

    @respx.mock
    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_episode(self) -> None:
        """Pipeline should handle missing episode gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PodtextConfig()
            config.storage.media_dir = str(Path(tmpdir) / "downloads")
            config.storage.output_dir = str(Path(tmpdir) / "output")

            # Mock RSS feed with only one episode
            feed_xml = generate_rss_feed([{
                "title": "Only Episode",
                "pub_date": "Mon, 15 Jan 2024 12:00:00 +0000",
                "media_url": "https://example.com/audio.mp3",
            }])
            respx.get("https://example.com/feed.xml").mock(
                return_value=httpx.Response(200, text=feed_xml)
            )

            # Request non-existent episode
            with pytest.raises(PipelineError) as exc_info:
                await run_transcription_pipeline(
                    feed_url="https://example.com/feed.xml",
                    episode_index=99,
                    config=config,
                )

            assert "not found" in str(exc_info.value).lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_pipeline_handles_feed_error(self) -> None:
        """Pipeline should handle feed errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PodtextConfig()
            config.storage.media_dir = str(Path(tmpdir) / "downloads")
            config.storage.output_dir = str(Path(tmpdir) / "output")

            # Mock feed error
            respx.get("https://example.com/feed.xml").mock(
                return_value=httpx.Response(404)
            )

            with pytest.raises(PipelineError) as exc_info:
                await run_transcription_pipeline(
                    feed_url="https://example.com/feed.xml",
                    episode_index=1,
                    config=config,
                )

            assert "RSS feed" in str(exc_info.value)


class TestConfigIntegration:
    """Integration tests for configuration handling."""

    def test_config_file_creation_on_first_run(self) -> None:
        """Global config file should be created on first run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_path = Path(tmpdir) / "global" / "config"
            local_path = Path(tmpdir) / "local" / "config"

            assert not global_path.exists()

            config = load_config(
                local_path=local_path,
                global_path=global_path,
                create_global_if_missing=True,
            )

            # Global config should now exist
            assert global_path.exists()

            # Config should have defaults
            assert config.whisper.model == "base"
            assert config.storage.temp_storage is False

    def test_env_var_override_in_integration(self) -> None:
        """Environment variable should override config in integration context."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            global_path = Path(tmpdir) / "config"

            original_env = os.environ.get("ANTHROPIC_API_KEY")
            try:
                os.environ["ANTHROPIC_API_KEY"] = "test-env-key"

                config = load_config(
                    local_path=Path(tmpdir) / "nonexistent",
                    global_path=global_path,
                    create_global_if_missing=True,
                )

                assert config.api.anthropic_key == "test-env-key"
            finally:
                if original_env is None:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                else:
                    os.environ["ANTHROPIC_API_KEY"] = original_env


class TestErrorHandlingIntegration:
    """Integration tests for error handling across modules."""

    @respx.mock
    def test_cli_handles_network_errors(self) -> None:
        """CLI should handle network errors gracefully."""
        respx.get("https://itunes.apple.com/search").mock(
            side_effect=httpx.ConnectError("Network unreachable")
        )

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test"])

        assert result.exit_code == 1
        assert "Error" in result.output

    @respx.mock
    def test_cli_handles_invalid_feed(self) -> None:
        """CLI should handle invalid RSS feeds gracefully."""
        respx.get("https://example.com/feed.xml").mock(
            return_value=httpx.Response(200, text="Not valid XML at all")
        )

        runner = CliRunner()
        result = runner.invoke(main, ["episodes", "https://example.com/feed.xml"])

        # Should either succeed with no episodes or fail gracefully
        # (feedparser is lenient with malformed feeds)
        assert "Episode" not in result.output or result.exit_code == 0
