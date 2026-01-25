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


from html.parser import HTMLParser
from typing import Any


class _HTMLToMarkdownParser(HTMLParser):
    """HTML parser that converts HTML to markdown format.
    
    Handles common HTML elements found in podcast show notes.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.result: list[str] = []
        self.current_link_url: str | None = None
        self.current_link_text: list[str] = []
        self.in_link = False
        self.list_stack: list[str] = []  # Track nested lists ('ul' or 'ol')
        self.list_item_count: list[int] = []  # Track item numbers for ol
        
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        
        if tag == "a":
            self.in_link = True
            self.current_link_text = []
            # Find href attribute
            for attr_name, attr_value in attrs:
                if attr_name == "href" and attr_value:
                    self.current_link_url = attr_value
                    break
        elif tag == "p":
            if self.result and not self.result[-1].endswith("\n\n"):
                self.result.append("\n\n")
        elif tag == "br":
            self.result.append("\n")
        elif tag in ("strong", "b"):
            self.result.append("**")
        elif tag in ("em", "i"):
            self.result.append("*")
        elif tag == "code":
            self.result.append("`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
            self.result.append("#" * level + " ")
        elif tag == "ul":
            self.list_stack.append("ul")
            self.list_item_count.append(0)
        elif tag == "ol":
            self.list_stack.append("ol")
            self.list_item_count.append(0)
        elif tag == "li":
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
            indent = "  " * (len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == "ol":
                self.list_item_count[-1] += 1
                self.result.append(f"{indent}{self.list_item_count[-1]}. ")
            else:
                self.result.append(f"{indent}- ")
    
    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        
        if tag == "a":
            if self.in_link and self.current_link_url:
                link_text = "".join(self.current_link_text).strip()
                if link_text:
                    self.result.append(f"[{link_text}]({self.current_link_url})")
                else:
                    self.result.append(self.current_link_url)
            self.in_link = False
            self.current_link_url = None
            self.current_link_text = []
        elif tag == "p":
            self.result.append("\n\n")
        elif tag in ("strong", "b"):
            self.result.append("**")
        elif tag in ("em", "i"):
            self.result.append("*")
        elif tag == "code":
            self.result.append("`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.result.append("\n\n")
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            if self.list_item_count:
                self.list_item_count.pop()
            if not self.list_stack:
                self.result.append("\n")
        elif tag == "li":
            pass  # Newline handled by next li or end of list
    
    def handle_data(self, data: str) -> None:
        if self.in_link:
            self.current_link_text.append(data)
        else:
            self.result.append(data)
    
    def get_result(self) -> str:
        return "".join(self.result)


def convert_html_to_markdown(html_content: str) -> str:
    """Convert HTML content to markdown format.
    
    Handles common HTML elements found in podcast show notes:
    - Links (<a>) → [text](url)
    - Lists (<ul>, <ol>, <li>) → markdown lists
    - Headings (<h1>-<h6>) → # headings
    - Paragraphs (<p>) → double newlines
    - Bold/italic → **bold**, *italic*
    - Strips unsupported tags, preserves text
    
    Args:
        html_content: HTML string to convert.
        
    Returns:
        Markdown-formatted string.
        
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1
    """
    if not html_content:
        return ""
    
    # Check if content appears to be plain text (no HTML tags)
    if "<" not in html_content:
        return html_content
    
    try:
        parser = _HTMLToMarkdownParser()
        parser.feed(html_content)
        result = parser.get_result()
        
        # Clean up excessive whitespace
        import re
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = result.strip()
        
        return result
    except Exception:
        # On any parsing error, return the original content stripped of tags
        import re
        return re.sub(r"<[^>]+>", "", html_content).strip()
