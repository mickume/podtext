"""Media file downloader for podcast episodes."""

import os
from pathlib import Path
from urllib.parse import urlparse

import httpx


class DownloadError(Exception):
    """Exception raised when media download fails."""

    pass


def _get_filename_from_url(url: str) -> str:
    """Extract filename from URL or generate a default."""
    parsed = urlparse(url)
    path = parsed.path

    if path:
        filename = os.path.basename(path)
        if filename:
            return filename

    return "episode.mp3"


async def download_media(
    url: str,
    dest_dir: Path | str,
    filename: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> Path:
    """
    Download a media file from URL to destination directory.

    Args:
        url: URL of the media file to download
        dest_dir: Directory to save the downloaded file
        filename: Optional filename override (default: extracted from URL)
        client: Optional httpx client for testing

    Returns:
        Path to the downloaded file

    Raises:
        DownloadError: If the download fails
    """
    dest_dir = Path(dest_dir)

    # Create destination directory if needed
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename
    if filename is None:
        filename = _get_filename_from_url(url)

    dest_path = dest_dir / filename

    should_close_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=300.0, follow_redirects=True)

    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            with open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    except httpx.HTTPStatusError as e:
        raise DownloadError(f"Failed to download media: HTTP {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise DownloadError(f"Failed to connect for media download: {e}") from e
    except OSError as e:
        raise DownloadError(f"Failed to write media file: {e}") from e
    finally:
        if should_close_client:
            await client.aclose()

    return dest_path


def cleanup_media_file(file_path: Path) -> bool:
    """
    Delete a media file (for temporary storage cleanup).

    Args:
        file_path: Path to the file to delete

    Returns:
        True if file was deleted, False if it didn't exist
    """
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except OSError:
        return False
