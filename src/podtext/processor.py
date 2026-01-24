"""Post-processing for transcription output."""

AD_REMOVED_MARKER = "[ADVERTISEMENT WAS REMOVED]"


def remove_advertisements(
    text: str,
    ad_markers: list[tuple[int, int]],
) -> str:
    """
    Remove advertisement sections from text and insert markers.

    Args:
        text: The original transcript text
        ad_markers: List of (start, end) position tuples for advertisements

    Returns:
        Text with advertisements removed and markers inserted
    """
    if not ad_markers:
        return text

    # Sort markers by start position (descending) to process from end
    # This prevents position shifts from affecting earlier markers
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

        # Remove the advertisement content and insert marker
        result = result[:start] + AD_REMOVED_MARKER + result[end:]

    return result


def count_removed_ads(text: str) -> int:
    """
    Count the number of advertisement removal markers in text.

    Args:
        text: The processed text

    Returns:
        Number of advertisement markers found
    """
    return text.count(AD_REMOVED_MARKER)


def validate_ad_removal(
    original_text: str,
    processed_text: str,
    ad_markers: list[tuple[int, int]],
) -> bool:
    """
    Validate that advertisement removal was performed correctly.

    Checks that:
    1. Number of markers equals number of ad sections removed
    2. Original ad content is not in processed text

    Args:
        original_text: The original transcript
        processed_text: The processed transcript
        ad_markers: List of advertisement positions

    Returns:
        True if validation passes
    """
    # Check marker count
    marker_count = count_removed_ads(processed_text)
    if marker_count != len(ad_markers):
        return False

    # Check that ad content is removed
    for start, end in ad_markers:
        if start < 0:
            start = 0
        if end > len(original_text):
            end = len(original_text)
        if start >= end:
            continue

        ad_content = original_text[start:end]
        # The exact ad content should not appear in processed text
        # (unless the marker happens to contain it, which is unlikely)
        if ad_content in processed_text and ad_content != AD_REMOVED_MARKER:
            return False

    return True
