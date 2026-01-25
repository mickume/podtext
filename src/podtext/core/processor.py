"""Text processor for Podtext.

Handles post-processing of transcribed text including advertisement removal
and path sanitization for file naming.

Requirements: 6.2, 6.3
"""

from __future__ import annotations

import re


# Marker text inserted where advertisements are removed
ADVERTISEMENT_MARKER = "ADVERTISEMENT WAS REMOVED"

# Characters invalid in file paths (covers Windows, macOS, Linux)
INVALID_PATH_CHARS = re.compile(r'[/\\:*?"<>|]')


def sanitize_path_component(
    name: str,
    max_length: int = 30,
    fallback: str = "unknown",
) -> str:
    """Sanitize a string for use as a file system path component.
    
    Processes the input string to make it safe for use as a directory name
    or filename by:
    1. Replacing invalid characters with underscores
    2. Collapsing consecutive underscores
    3. Trimming whitespace and underscores
    4. Truncating to max_length, preferring word boundaries
    5. Returning fallback if result would be empty
    
    Args:
        name: The string to sanitize (podcast name or episode title).
        max_length: Maximum length of the result (default: 30).
        fallback: Value to return if sanitization results in empty string.
        
    Returns:
        A sanitized string safe for use in file paths.
        
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.3
    
    Example:
        >>> sanitize_path_component("Episode: The Beginning")
        'Episode_ The Beginning'
        >>> sanitize_path_component("A/B Testing")
        'A_B Testing'
        >>> sanitize_path_component("")
        'unknown'
        >>> sanitize_path_component("This is a very long episode title that exceeds the limit")
        'This is a very long episode'
    """
    if not name:
        return fallback
    
    # Replace invalid characters with underscores
    result = INVALID_PATH_CHARS.sub("_", name)
    
    # Collapse consecutive underscores into single underscore
    result = re.sub(r"_+", "_", result)
    
    # Trim leading/trailing whitespace and underscores
    result = result.strip().strip("_").strip()
    
    # If empty after processing, return fallback
    if not result:
        return fallback
    
    # Truncate to max_length, preferring word boundaries
    if len(result) > max_length:
        result = _truncate_at_word_boundary(result, max_length)
    
    # Final trim of any trailing whitespace or underscores from truncation
    result = result.strip().rstrip("_").strip()
    
    # If empty after truncation, return fallback
    if not result:
        return fallback
    
    return result


def _truncate_at_word_boundary(text: str, max_length: int) -> str:
    """Truncate text at a word boundary if possible.
    
    Attempts to truncate at the last space before max_length.
    If no space is found, truncates at max_length.
    
    Args:
        text: The text to truncate.
        max_length: Maximum length of the result.
        
    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    
    # Find the last space before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    
    # If we found a space and it's not too early in the string
    # (keep at least 10 chars to avoid overly short results)
    if last_space > 10:
        return truncated[:last_space]
    
    return truncated


def _normalize_ad_blocks(
    ad_positions: list[tuple[int, int]],
    text_length: int,
) -> list[tuple[int, int]]:
    """Normalize and merge overlapping/adjacent advertisement blocks.
    
    This function:
    1. Filters out invalid positions (negative, out of bounds, empty ranges)
    2. Clamps positions to valid text bounds
    3. Sorts blocks by start position
    4. Merges overlapping or adjacent blocks
    
    Args:
        ad_positions: List of (start, end) tuples for advertisement positions.
        text_length: Length of the text being processed.
        
    Returns:
        Normalized list of non-overlapping (start, end) tuples, sorted by start.
    """
    if not ad_positions or text_length <= 0:
        return []
    
    # Filter and clamp positions
    valid_blocks: list[tuple[int, int]] = []
    for start, end in ad_positions:
        # Skip invalid ranges
        if start >= end:
            continue
        if start >= text_length:
            continue
        if end <= 0:
            continue
            
        # Clamp to valid bounds
        clamped_start = max(0, start)
        clamped_end = min(text_length, end)
        
        # Only add if still valid after clamping
        if clamped_start < clamped_end:
            valid_blocks.append((clamped_start, clamped_end))
    
    if not valid_blocks:
        return []
    
    # Sort by start position
    valid_blocks.sort(key=lambda x: x[0])
    
    # Merge overlapping/adjacent blocks
    merged: list[tuple[int, int]] = []
    current_start, current_end = valid_blocks[0]
    
    for start, end in valid_blocks[1:]:
        if start <= current_end:
            # Overlapping or adjacent - extend current block
            current_end = max(current_end, end)
        else:
            # Gap between blocks - save current and start new
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Don't forget the last block
    merged.append((current_start, current_end))
    
    return merged


def remove_advertisements(
    text: str,
    ad_positions: list[tuple[int, int]],
) -> str:
    """Remove advertisement blocks from text and insert markers.
    
    Takes transcript text and a list of (start, end) character positions
    identifying advertisement blocks. Removes the ad content and inserts
    "ADVERTISEMENT WAS REMOVED" marker at each removal location.
    
    Handles:
    - Overlapping ad blocks (merged into single removal)
    - Adjacent ad blocks (merged into single removal)
    - Out-of-bounds positions (clamped or ignored)
    - Empty or invalid inputs
    
    Args:
        text: The transcript text to process.
        ad_positions: List of (start, end) tuples indicating advertisement
            character positions. Positions are 0-indexed, with end being
            exclusive (like Python slice notation).
            
    Returns:
        Processed text with advertisements removed and markers inserted.
        
    Validates: Requirements 6.2, 6.3
    
    Example:
        >>> text = "Hello this is an ad buy now! Goodbye"
        >>> ad_positions = [(6, 28)]  # "this is an ad buy now!"
        >>> remove_advertisements(text, ad_positions)
        'Hello [ADVERTISEMENT WAS REMOVED] Goodbye'
    """
    if not text:
        return text
    
    if not ad_positions:
        return text
    
    # Normalize ad blocks (filter, clamp, sort, merge)
    normalized = _normalize_ad_blocks(ad_positions, len(text))
    
    if not normalized:
        return text
    
    # Build result by keeping non-ad sections and inserting markers
    result_parts: list[str] = []
    current_pos = 0
    
    for ad_start, ad_end in normalized:
        # Add text before this ad block
        if current_pos < ad_start:
            result_parts.append(text[current_pos:ad_start])
        
        # Add the marker (with brackets for visibility)
        result_parts.append(f"[{ADVERTISEMENT_MARKER}]")
        
        # Move past the ad block
        current_pos = ad_end
    
    # Add any remaining text after the last ad block
    if current_pos < len(text):
        result_parts.append(text[current_pos:])
    
    return "".join(result_parts)
