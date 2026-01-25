"""Text processor for Podtext.

Handles post-processing of transcribed text including advertisement removal.

Requirements: 6.2, 6.3
"""

from __future__ import annotations


# Marker text inserted where advertisements are removed
ADVERTISEMENT_MARKER = "ADVERTISEMENT WAS REMOVED"


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
