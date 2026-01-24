"""Text processing utilities."""

import re


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use as a filename.

    Args:
        text: Text to sanitize

    Returns:
        Safe filename string
    """
    # Remove/replace problematic characters
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    # Replace spaces with dashes
    text = re.sub(r"\s+", "-", text)
    # Remove multiple dashes
    text = re.sub(r"-+", "-", text)
    # Remove leading/trailing dashes
    text = text.strip("-")
    return text


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as timestamp string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp (HH:MM:SS or MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())
