"""Audio processing utilities."""

from pathlib import Path


def get_audio_duration(path: Path) -> float:
    """
    Get the duration of an audio file in seconds.

    Args:
        path: Path to the audio file

    Returns:
        Duration in seconds
    """
    try:
        import ffmpeg

        probe = ffmpeg.probe(str(path))
        duration = float(probe["format"]["duration"])
        return duration
    except Exception:
        return 0.0


def is_audio_file(path: Path) -> bool:
    """Check if a file is an audio file based on extension."""
    audio_extensions = {
        ".mp3",
        ".m4a",
        ".wav",
        ".flac",
        ".ogg",
        ".wma",
        ".aac",
        ".opus",
    }
    return path.suffix.lower() in audio_extensions


def is_video_file(path: Path) -> bool:
    """Check if a file is a video file based on extension."""
    video_extensions = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm", ".flv"}
    return path.suffix.lower() in video_extensions
