"""Post-processing for transcripts.

Handles advertisement removal and text processing.
"""


AD_MARKER = "[ADVERTISEMENT WAS REMOVED]"


def remove_advertisements(text: str, ad_markers: list[tuple[int, int]]) -> str:
    """Remove advertisements from transcript text.

    Args:
        text: Original transcript text.
        ad_markers: List of (start, end) tuples marking advertisement positions.

    Returns:
        Text with advertisements replaced by markers.
    """
    if not ad_markers:
        return text

    # Sort markers by start position in reverse order
    # This allows us to replace from end to start without affecting positions
    sorted_markers = sorted(ad_markers, key=lambda x: x[0], reverse=True)

    result = text
    for start, end in sorted_markers:
        # Validate positions
        if start < 0:
            start = 0
        if end > len(result):
            end = len(result)
        if start >= end:
            continue

        # Replace advertisement with marker
        result = result[:start] + AD_MARKER + result[end:]

    return result


def count_removed_ads(text: str) -> int:
    """Count the number of removed advertisement markers in text.

    Args:
        text: Processed text.

    Returns:
        Number of AD_MARKER occurrences.
    """
    return text.count(AD_MARKER)


def format_paragraphs(paragraphs: list[str]) -> str:
    """Format paragraphs into readable text.

    Args:
        paragraphs: List of paragraph strings.

    Returns:
        Formatted text with double newlines between paragraphs.
    """
    return "\n\n".join(p.strip() for p in paragraphs if p.strip())
