"""Property-based tests for Media/Transcription.

Feature: podtext
Tests media storage location, temporary file cleanup, config model propagation,
and language check bypass.

Validates: Requirements 3.2, 3.3, 4.2, 5.3
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from podtext.core.config import (
    VALID_WHISPER_MODELS,
    Config,
    StorageConfig,
)
from podtext.services.downloader import (
    cleanup_media_file,
    download_media,
    download_media_to_config_dir,
    download_with_optional_cleanup,
)
from podtext.services.transcriber import (
    TranscriptionResult,
    transcribe,
    transcribe_with_config,
)

# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for valid whisper model names
whisper_model_strategy = st.sampled_from(list(VALID_WHISPER_MODELS))

# Strategy for valid directory names (simple alphanumeric)
dir_name_strategy = st.from_regex(
    r"[a-zA-Z][a-zA-Z0-9_-]{0,20}",
    fullmatch=True,
)

# Strategy for valid filenames (simple alphanumeric with extension)
filename_strategy = st.from_regex(
    r"[a-zA-Z][a-zA-Z0-9_-]{0,15}\.(mp3|m4a|wav|ogg|mp4)",
    fullmatch=True,
)


# Strategy for generating nested directory paths
@st.composite
def nested_path_strategy(draw: st.DrawFn) -> str:
    """Generate a nested directory path."""
    depth = draw(st.integers(min_value=1, max_value=3))
    parts = [draw(dir_name_strategy) for _ in range(depth)]
    return "/".join(parts)


# Strategy for generating valid URLs
@st.composite
def media_url_strategy(draw: st.DrawFn) -> str:
    """Generate a valid media URL."""
    domain = draw(st.from_regex(r"[a-z]{3,10}", fullmatch=True))
    path = draw(st.from_regex(r"[a-z0-9/]{1,20}", fullmatch=True))
    filename = draw(filename_strategy)
    return f"https://{domain}.com/{path}/{filename}"


# Strategy for language codes
language_code_strategy = st.sampled_from(
    ["en", "es", "fr", "de", "ja", "zh", "ko", "pt", "it", "ru"]
)


# =============================================================================
# Property 5: Media Storage Location
# =============================================================================


class TestMediaStorageLocation:
    """Property 5: Media Storage Location

    Feature: podtext, Property 5: Media Storage Location

    For any configuration with media_dir set to path P, downloaded media files
    SHALL be stored within path P.

    **Validates: Requirements 3.2**
    """

    @settings(max_examples=100)
    @given(
        subdir=nested_path_strategy(),
        filename=filename_strategy,
    )
    def test_downloaded_file_stored_in_config_media_dir(
        self,
        subdir: str,
        filename: str,
    ) -> None:
        """Property 5: Media Storage Location

        Feature: podtext, Property 5: Media Storage Location

        For any configuration with media_dir set to path P, downloaded media files
        SHALL be stored within path P.

        **Validates: Requirements 3.2**
        """
        # Create a unique temp directory for this test
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        media_dir = base_dir / f"media_{unique_id}" / subdir

        try:
            # Create config with the generated media_dir path
            config = Config(storage=StorageConfig(media_dir=str(media_dir)))

            # Mock the HTTP download to avoid network calls
            test_content = b"fake audio content for testing"

            with patch("podtext.services.downloader.httpx.stream") as mock_stream:
                mock_response = MagicMock()
                mock_response.iter_bytes.return_value = [test_content]
                mock_response.raise_for_status = MagicMock()
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_stream.return_value = mock_response

                # Download media to config directory
                result_path = download_media_to_config_dir(
                    f"https://example.com/podcast/{filename}",
                    config,
                    filename=filename,
                )

                # Property: Downloaded file SHALL be stored within path P (media_dir)
                assert result_path.exists(), f"Downloaded file should exist at {result_path}"

                # Verify the file is within the configured media_dir
                assert str(result_path).startswith(str(media_dir)), (
                    f"Downloaded file '{result_path}' should be within "
                    f"configured media_dir '{media_dir}'"
                )

                # Verify the file is a direct child of media_dir
                assert result_path.parent == media_dir, (
                    f"Downloaded file parent '{result_path.parent}' should be "
                    f"exactly the configured media_dir '{media_dir}'"
                )

                # Verify the content was written correctly
                assert result_path.read_bytes() == test_content, (
                    "Downloaded file content should match expected content"
                )
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        media_dir_name=dir_name_strategy,
        filename=filename_strategy,
    )
    def test_download_media_respects_dest_path(
        self,
        media_dir_name: str,
        filename: str,
    ) -> None:
        """Property 5: Media Storage Location - Direct download_media

        Feature: podtext, Property 5: Media Storage Location

        For any destination path P provided to download_media, the downloaded
        file SHALL be stored at exactly path P.

        **Validates: Requirements 3.2**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        dest_path = base_dir / f"{media_dir_name}_{unique_id}" / filename

        try:
            test_content = b"test audio data"

            with patch("podtext.services.downloader.httpx.stream") as mock_stream:
                mock_response = MagicMock()
                mock_response.iter_bytes.return_value = [test_content]
                mock_response.raise_for_status = MagicMock()
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_stream.return_value = mock_response

                result_path = download_media(
                    f"https://example.com/{filename}",
                    dest_path,
                )

                # Property: Downloaded file SHALL be stored at exactly the specified path
                assert result_path == dest_path, (
                    f"Returned path '{result_path}' should equal destination path '{dest_path}'"
                )
                assert dest_path.exists(), f"File should exist at destination path '{dest_path}'"
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)


# =============================================================================
# Property 6: Temporary File Cleanup
# =============================================================================


class TestTemporaryFileCleanup:
    """Property 6: Temporary File Cleanup

    Feature: podtext, Property 6: Temporary File Cleanup

    For any transcription operation with temp_storage=true, after completion
    the media file SHALL not exist on disk.

    **Validates: Requirements 3.3**
    """

    @settings(max_examples=100)
    @given(
        filename=filename_strategy,
        subdir=dir_name_strategy,
    )
    def test_media_file_deleted_after_context_exit_with_temp_storage(
        self,
        filename: str,
        subdir: str,
    ) -> None:
        """Property 6: Temporary File Cleanup

        Feature: podtext, Property 6: Temporary File Cleanup

        For any transcription operation with temp_storage=true, after completion
        the media file SHALL not exist on disk.

        **Validates: Requirements 3.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        media_dir = base_dir / f"media_{unique_id}" / subdir

        try:
            # Create config with temp_storage=True
            config = Config(
                storage=StorageConfig(
                    media_dir=str(media_dir),
                    temp_storage=True,  # Key: temp_storage is enabled
                )
            )

            test_content = b"temporary audio content"

            with patch("podtext.services.downloader.httpx.stream") as mock_stream:
                mock_response = MagicMock()
                mock_response.iter_bytes.return_value = [test_content]
                mock_response.raise_for_status = MagicMock()
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_stream.return_value = mock_response

                # Use the context manager that respects temp_storage config
                file_path_during_context = None
                with download_with_optional_cleanup(
                    f"https://example.com/{filename}",
                    config,
                    filename=filename,
                ) as file_path:
                    file_path_during_context = file_path
                    # File should exist during the context
                    assert file_path.exists(), f"File should exist during context at '{file_path}'"

                # Property: After completion, media file SHALL not exist on disk
                assert not file_path_during_context.exists(), (
                    f"With temp_storage=True, file '{file_path_during_context}' "
                    "should NOT exist after context exit"
                )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        filename=filename_strategy,
        subdir=dir_name_strategy,
    )
    def test_media_file_persists_when_temp_storage_false(
        self,
        filename: str,
        subdir: str,
    ) -> None:
        """Property 6: Temporary File Cleanup - Inverse

        Feature: podtext, Property 6: Temporary File Cleanup

        For any transcription operation with temp_storage=false, after completion
        the media file SHALL still exist on disk.

        **Validates: Requirements 3.2, 3.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        media_dir = base_dir / f"media_{unique_id}" / subdir

        try:
            # Create config with temp_storage=False
            config = Config(
                storage=StorageConfig(
                    media_dir=str(media_dir),
                    temp_storage=False,  # Key: temp_storage is disabled
                )
            )

            test_content = b"persistent audio content"

            with patch("podtext.services.downloader.httpx.stream") as mock_stream:
                mock_response = MagicMock()
                mock_response.iter_bytes.return_value = [test_content]
                mock_response.raise_for_status = MagicMock()
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_stream.return_value = mock_response

                file_path_during_context = None
                with download_with_optional_cleanup(
                    f"https://example.com/{filename}",
                    config,
                    filename=filename,
                ) as file_path:
                    file_path_during_context = file_path
                    assert file_path.exists(), f"File should exist during context at '{file_path}'"

                # With temp_storage=False, file should still exist after context
                assert file_path_during_context.exists(), (
                    f"With temp_storage=False, file '{file_path_during_context}' "
                    "should still exist after context exit"
                )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        filename=filename_strategy,
    )
    def test_cleanup_media_file_removes_existing_file(
        self,
        filename: str,
    ) -> None:
        """Property 6: Temporary File Cleanup - cleanup_media_file function

        Feature: podtext, Property 6: Temporary File Cleanup

        The cleanup_media_file function SHALL remove the specified file from disk.

        **Validates: Requirements 3.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        file_path = base_dir / f"test_{unique_id}" / filename

        try:
            # Create the file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"content to be deleted")

            assert file_path.exists(), "File should exist before cleanup"

            # Call cleanup
            result = cleanup_media_file(file_path)

            # Property: After cleanup, file SHALL not exist
            assert result is True, "cleanup_media_file should return True for existing file"
            assert not file_path.exists(), (
                f"After cleanup_media_file, file '{file_path}' should NOT exist"
            )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)


# =============================================================================
# Property 7: Config Model Propagation
# =============================================================================


class TestConfigModelPropagation:
    """Property 7: Config Model Propagation

    Feature: podtext, Property 7: Config Model Propagation

    For any configuration with whisper.model set to M, the transcription function
    SHALL be called with model parameter M.

    **Validates: Requirements 4.2**
    """

    @settings(max_examples=100)
    @given(
        model=whisper_model_strategy,
    )
    def test_transcribe_uses_specified_model(
        self,
        model: str,
    ) -> None:
        """Property 7: Config Model Propagation

        Feature: podtext, Property 7: Config Model Propagation

        For any configuration with whisper.model set to M, the transcription function
        SHALL be called with model parameter M.

        **Validates: Requirements 4.2**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            # Create a fake audio file
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True):
                with patch("podtext.services.transcriber.mlx_whisper") as mock_mlx:
                    mock_mlx.transcribe.return_value = {
                        "text": "Test transcription",
                        "segments": [{"text": "Test transcription."}],
                        "language": "en",
                    }

                    # Call transcribe with the specified model
                    transcribe(audio_file, model=model)

                    # Property: transcription function SHALL be called with model parameter M
                    mock_mlx.transcribe.assert_called_once()
                    call_args = mock_mlx.transcribe.call_args

                    # Verify the model path contains the specified model
                    path_or_hf_repo = call_args.kwargs.get("path_or_hf_repo", "")
                    assert f"whisper-{model}" in path_or_hf_repo, (
                        f"Transcription should use model '{model}', "
                        f"but path_or_hf_repo was '{path_or_hf_repo}'"
                    )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        model=whisper_model_strategy,
    )
    def test_transcribe_with_config_propagates_model(
        self,
        model: str,
    ) -> None:
        """Property 7: Config Model Propagation - transcribe_with_config

        Feature: podtext, Property 7: Config Model Propagation

        For any model M passed to transcribe_with_config, the underlying
        transcribe function SHALL be called with model parameter M.

        **Validates: Requirements 4.2**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.transcribe") as mock_transcribe:
                mock_transcribe.return_value = TranscriptionResult(
                    text="Test",
                    paragraphs=["Test."],
                    language="en",
                )

                # Call transcribe_with_config with the specified model
                transcribe_with_config(audio_file, model=model)

                # Property: transcribe SHALL be called with model parameter M
                mock_transcribe.assert_called_once()
                call_args = mock_transcribe.call_args

                # The model should be passed as the second positional argument
                assert call_args[0][1] == model, (
                    f"transcribe should be called with model '{model}', "
                    f"but was called with '{call_args[0][1]}'"
                )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        model1=whisper_model_strategy,
        model2=whisper_model_strategy,
    )
    def test_different_models_produce_different_calls(
        self,
        model1: str,
        model2: str,
    ) -> None:
        """Property 7: Config Model Propagation - Model Distinction

        Feature: podtext, Property 7: Config Model Propagation

        For any two different models M1 and M2, the transcription function
        SHALL be called with different model parameters.

        **Validates: Requirements 4.2**
        """
        # Only test when models are different
        assume(model1 != model2)

        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True):
                with patch("podtext.services.transcriber.mlx_whisper") as mock_mlx:
                    mock_mlx.transcribe.return_value = {
                        "text": "Test",
                        "segments": [],
                        "language": "en",
                    }

                    # Call with first model
                    transcribe(audio_file, model=model1)
                    call1_path = mock_mlx.transcribe.call_args.kwargs.get("path_or_hf_repo", "")

                    mock_mlx.reset_mock()

                    # Call with second model
                    transcribe(audio_file, model=model2)
                    call2_path = mock_mlx.transcribe.call_args.kwargs.get("path_or_hf_repo", "")

                    # Property: Different models SHALL produce different path_or_hf_repo values
                    assert call1_path != call2_path, (
                        f"Different models '{model1}' and '{model2}' should produce "
                        f"different paths, but both got '{call1_path}'"
                    )
                    assert f"whisper-{model1}" in call1_path, (
                        f"First call should use model '{model1}'"
                    )
                    assert f"whisper-{model2}" in call2_path, (
                        f"Second call should use model '{model2}'"
                    )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)


# =============================================================================
# Property 9: Language Check Bypass
# =============================================================================


class TestLanguageCheckBypass:
    """Property 9: Language Check Bypass

    Feature: podtext, Property 9: Language Check Bypass

    For any transcription operation with skip-language-check flag set,
    the language detection function SHALL not be called.

    **Validates: Requirements 5.3**
    """

    @settings(max_examples=100)
    @given(
        detected_language=language_code_strategy,
    )
    def test_language_detection_bypassed_when_skip_flag_set(
        self,
        detected_language: str,
    ) -> None:
        """Property 9: Language Check Bypass

        Feature: podtext, Property 9: Language Check Bypass

        For any transcription operation with skip-language-check flag set,
        the language detection function SHALL not be called.

        **Validates: Requirements 5.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True):
                with patch("podtext.services.transcriber.mlx_whisper") as mock_mlx:
                    with patch("podtext.services.transcriber._detect_language") as mock_detect:
                        with patch("podtext.services.transcriber._warn_non_english") as mock_warn:
                            mock_mlx.transcribe.return_value = {
                                "text": "Test transcription",
                                "segments": [{"text": "Test."}],
                                "language": detected_language,
                            }

                            # Call transcribe with skip_language_check=True
                            result = transcribe(
                                audio_file,
                                skip_language_check=True,
                            )

                            # Property: language detection function SHALL not be called
                            mock_detect.assert_not_called()

                            # Also verify warning is not called
                            mock_warn.assert_not_called()

                            # Language should be set to "unknown" when skipped
                            assert result.language == "unknown", (
                                f"When skip_language_check=True, language should be 'unknown', "
                                f"but got '{result.language}'"
                            )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        detected_language=language_code_strategy,
    )
    def test_language_detection_called_when_skip_flag_not_set(
        self,
        detected_language: str,
    ) -> None:
        """Property 9: Language Check Bypass - Inverse

        Feature: podtext, Property 9: Language Check Bypass

        For any transcription operation WITHOUT skip-language-check flag,
        the language detection SHALL be performed.

        **Validates: Requirements 5.1, 5.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True):
                with patch("podtext.services.transcriber.mlx_whisper") as mock_mlx:
                    mock_mlx.transcribe.return_value = {
                        "text": "Test transcription",
                        "segments": [{"text": "Test."}],
                        "language": detected_language,
                    }

                    # Call transcribe with skip_language_check=False (default)
                    result = transcribe(
                        audio_file,
                        skip_language_check=False,
                    )

                    # Language detection should be performed
                    # The result should contain the detected language
                    assert result.language == detected_language, (
                        f"When skip_language_check=False, "
                        f"language should be '{detected_language}', "
                        f"but got '{result.language}'"
                    )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        non_english_language=st.sampled_from(
            ["es", "fr", "de", "ja", "zh", "ko", "pt", "it", "ru"]
        ),
    )
    def test_no_warning_when_skip_flag_set_for_non_english(
        self,
        non_english_language: str,
    ) -> None:
        """Property 9: Language Check Bypass - No Warning

        Feature: podtext, Property 9: Language Check Bypass

        For any transcription operation with skip-language-check flag set,
        no language warning SHALL be displayed even for non-English content.

        **Validates: Requirements 5.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True):
                with patch("podtext.services.transcriber.mlx_whisper") as mock_mlx:
                    with patch("podtext.services.transcriber._warn_non_english") as mock_warn:
                        mock_mlx.transcribe.return_value = {
                            "text": "Contenido en otro idioma",
                            "segments": [{"text": "Contenido."}],
                            "language": non_english_language,
                        }

                        # Call transcribe with skip_language_check=True
                        result = transcribe(
                            audio_file,
                            skip_language_check=True,
                        )

                        # Property: No warning SHALL be displayed
                        mock_warn.assert_not_called()

                        # Language should be "unknown" when skipped
                        assert result.language == "unknown"
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        model=whisper_model_strategy,
    )
    def test_skip_language_check_works_with_any_model(
        self,
        model: str,
    ) -> None:
        """Property 9: Language Check Bypass - Model Independence

        Feature: podtext, Property 9: Language Check Bypass

        For any transcription operation with skip-language-check flag set,
        the language detection SHALL be bypassed regardless of the model used.

        **Validates: Requirements 4.2, 5.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        audio_file = base_dir / f"test_{unique_id}.mp3"

        try:
            audio_file.write_bytes(b"fake audio content")

            with patch("podtext.services.transcriber.MLX_WHISPER_AVAILABLE", True):
                with patch("podtext.services.transcriber.mlx_whisper") as mock_mlx:
                    with patch("podtext.services.transcriber._detect_language") as mock_detect:
                        mock_mlx.transcribe.return_value = {
                            "text": "Test",
                            "segments": [],
                            "language": "fr",
                        }

                        # Call transcribe with skip_language_check=True and specified model
                        result = transcribe(
                            audio_file,
                            model=model,
                            skip_language_check=True,
                        )

                        # Property: language detection SHALL not be called regardless of model
                        mock_detect.assert_not_called()

                        # Verify the correct model was still used
                        call_args = mock_mlx.transcribe.call_args
                        path_or_hf_repo = call_args.kwargs.get("path_or_hf_repo", "")
                        assert f"whisper-{model}" in path_or_hf_repo, (
                            f"Model '{model}' should still be used with skip_language_check"
                        )

                        # Language should be "unknown"
                        assert result.language == "unknown"
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)
