"""Media downloader for Podtext.

Downloads podcast media files from URLs and stores them in the configured
directory. Supports temporary storage with cleanup after transcription.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

import hashlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator
from urllib.parse import unquote, urlparse

import httpx

if TYPE_CHECKING:
    from podtext.core.config import Config

# Default timeout for downloads (in seconds)
DEFAULT_TIMEOUT = 300.0  # 5 minutes for large media files

# Chunk size for streaming downloads (64KB)
CHUNK_SIZE = 65536


class DownloadError(Exception):
    """Raised when media download fails.

    Validates: Requirements 3.4
    """


def _extract_filename_from_url(url: str) -> str:
    """Extract a filename from a URL.

    Args:
        url: The URL to extract filename from.

    Returns:
        Extracted filename or a hash-based fallback.
    """
    parsed = urlparse(url)
    path = unquote(parsed.path)

    if path:
        # Get the last component of the path
        filename = Path(path).name
        if filename and "." in filename:
            return filename

    # Fallback: generate filename from URL hash
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"media_{url_hash}"


def _ensure_directory_exists(directory: Path) -> None:
    """Ensure the target directory exists.

    Args:
        directory: Path to the directory.

    Raises:
        DownloadError: If directory cannot be created.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DownloadError(f"Failed to create directory {directory}: {e}") from e


def download_media(
    url: str,
    dest_path: Path,
    timeout: float = DEFAULT_TIMEOUT,
) -> Path:
    """Download media file from URL to destination path.

    Downloads the media file from the given URL and saves it to the
    specified destination path. Creates parent directories if needed.

    Args:
        url: URL of the media file to download.
        dest_path: Destination path where the file should be saved.
        timeout: Request timeout in seconds.

    Returns:
        Path to the downloaded file.

    Raises:
        DownloadError: If download fails for any reason.

    Validates: Requirements 3.1, 3.4
    """
    # Ensure parent directory exists
    _ensure_directory_exists(dest_path.parent)

    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
            response.raise_for_status()

            # Write content to file in chunks
            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                    f.write(chunk)

        return dest_path

    except httpx.TimeoutException as e:
        # Clean up partial download
        if dest_path.exists():
            dest_path.unlink()
        raise DownloadError(f"Download timed out for {url}: {e}") from e

    except httpx.HTTPStatusError as e:
        # Clean up partial download
        if dest_path.exists():
            dest_path.unlink()
        raise DownloadError(
            f"HTTP error {e.response.status_code} downloading {url}: {e}"
        ) from e

    except httpx.RequestError as e:
        # Clean up partial download
        if dest_path.exists():
            dest_path.unlink()
        raise DownloadError(f"Failed to download {url}: {e}") from e

    except OSError as e:
        # Clean up partial download
        if dest_path.exists():
            dest_path.unlink()
        raise DownloadError(f"Failed to write file {dest_path}: {e}") from e


def download_media_to_config_dir(
    url: str,
    config: Config,
    filename: str | None = None,
) -> Path:
    """Download media file to the configured media directory.

    Downloads the media file from the given URL and saves it to the
    media directory specified in the configuration.

    Args:
        url: URL of the media file to download.
        config: Application configuration.
        filename: Optional filename to use. If not provided, extracted from URL.

    Returns:
        Path to the downloaded file.

    Raises:
        DownloadError: If download fails for any reason.

    Validates: Requirements 3.1, 3.2, 3.4
    """
    if filename is None:
        filename = _extract_filename_from_url(url)

    dest_path = config.get_media_dir() / filename
    return download_media(url, dest_path)


def cleanup_media_file(file_path: Path) -> bool:
    """Delete a media file from disk.

    Used for temporary storage cleanup after transcription completes.

    Args:
        file_path: Path to the file to delete.

    Returns:
        True if file was deleted, False if it didn't exist.

    Validates: Requirements 3.3
    """
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except OSError:
        # Silently ignore cleanup failures
        return False


@contextmanager
def temporary_download(
    url: str,
    config: Config,
    filename: str | None = None,
) -> Iterator[Path]:
    """Context manager for temporary media downloads.

    Downloads the media file and automatically cleans it up when the
    context exits, regardless of whether temp_storage is configured.
    Use this when you always want cleanup behavior.

    Args:
        url: URL of the media file to download.
        config: Application configuration.
        filename: Optional filename to use.

    Yields:
        Path to the downloaded file.

    Raises:
        DownloadError: If download fails.

    Validates: Requirements 3.3
    """
    file_path = download_media_to_config_dir(url, config, filename)
    try:
        yield file_path
    finally:
        cleanup_media_file(file_path)


@contextmanager
def download_with_optional_cleanup(
    url: str,
    config: Config,
    filename: str | None = None,
) -> Iterator[Path]:
    """Context manager for media downloads with config-based cleanup.

    Downloads the media file and cleans it up only if temp_storage
    is enabled in the configuration.

    Args:
        url: URL of the media file to download.
        config: Application configuration.
        filename: Optional filename to use.

    Yields:
        Path to the downloaded file.

    Raises:
        DownloadError: If download fails.

    Validates: Requirements 3.2, 3.3
    """
    file_path = download_media_to_config_dir(url, config, filename)
    try:
        yield file_path
    finally:
        if config.storage.temp_storage:
            cleanup_media_file(file_path)


def handle_download_error(error: DownloadError) -> None:
    """Display download error message and exit gracefully.

    Args:
        error: The download error that occurred.

    Validates: Requirements 3.4
    """
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)
