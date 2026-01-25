"""Property-based tests for processor module.

Tests sanitize_path_component using Hypothesis to verify universal properties.
"""

from hypothesis import given, settings, strategies as st

from podtext.core.processor import sanitize_path_component


# Invalid characters that should be replaced
INVALID_CHARS = set('/\\:*?"<>|')


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=200))
def test_sanitization_no_invalid_characters(input_string: str) -> None:
    """Feature: semantic-file-naming, Property 2: Sanitization Correctness
    
    For any input string, the sanitized output shall contain no invalid
    file path characters.
    
    Validates: Requirements 2.1, 2.2
    """
    result = sanitize_path_component(input_string)
    
    # Verify no invalid characters in result
    for char in result:
        assert char not in INVALID_CHARS, f"Invalid char '{char}' found in result"


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=200))
def test_sanitization_no_consecutive_underscores(input_string: str) -> None:
    """Feature: semantic-file-naming, Property 2: Sanitization Correctness
    
    For any input string, the sanitized output shall contain no consecutive
    underscores.
    
    Validates: Requirements 2.5
    """
    result = sanitize_path_component(input_string)
    
    # Verify no consecutive underscores
    assert "__" not in result, f"Consecutive underscores found in '{result}'"


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=200))
def test_sanitization_trimmed(input_string: str) -> None:
    """Feature: semantic-file-naming, Property 2: Sanitization Correctness
    
    For any input string, the sanitized output shall have no leading or
    trailing whitespace or underscores.
    
    Validates: Requirements 2.4
    """
    result = sanitize_path_component(input_string)
    
    # Verify trimmed (no leading/trailing whitespace)
    assert result == result.strip(), f"Result '{result}' has leading/trailing whitespace"
    
    # Verify no leading underscore
    assert not result.startswith("_"), f"Result '{result}' starts with underscore"
    
    # Verify no trailing underscore (unless it's the fallback)
    if result != "unknown":
        assert not result.endswith("_"), f"Result '{result}' ends with underscore"


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=200))
def test_length_constraint(input_string: str) -> None:
    """Feature: semantic-file-naming, Property 3: Length Constraint
    
    For any input string of any length, the sanitized output shall be
    at most 30 characters long.
    
    Validates: Requirements 3.1
    """
    result = sanitize_path_component(input_string)
    
    assert len(result) <= 30, f"Result '{result}' exceeds 30 chars (len={len(result)})"


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=200))
def test_non_empty_output(input_string: str) -> None:
    """Feature: semantic-file-naming, Property 4: Non-Empty Output
    
    For any input string, the sanitized output shall be non-empty when
    a fallback value is provided.
    
    Validates: Requirements 4.3
    """
    result = sanitize_path_component(input_string, fallback="fallback")
    
    assert len(result) > 0, "Result should never be empty with fallback"


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=200))
def test_idempotence(input_string: str) -> None:
    """Feature: semantic-file-naming, Property 5: Sanitization Round-Trip Stability
    
    For any already-sanitized string, sanitizing it again shall produce
    the same result (idempotence).
    
    Validates: Requirements 2.1, 2.3, 2.4, 2.5, 3.1
    """
    first_pass = sanitize_path_component(input_string)
    second_pass = sanitize_path_component(first_pass)
    
    assert first_pass == second_pass, (
        f"Not idempotent: '{first_pass}' -> '{second_pass}'"
    )


# Unit test examples for edge cases
def test_empty_string_returns_fallback() -> None:
    """Test that empty string returns the fallback value."""
    assert sanitize_path_component("") == "unknown"
    assert sanitize_path_component("", fallback="default") == "default"


def test_only_invalid_chars_returns_fallback() -> None:
    """Test that string with only invalid characters returns fallback."""
    assert sanitize_path_component("***") == "unknown"
    assert sanitize_path_component("/\\:") == "unknown"
    assert sanitize_path_component('?"<>|') == "unknown"


def test_valid_characters_preserved() -> None:
    """Test that valid characters are preserved."""
    assert sanitize_path_component("Hello World") == "Hello World"
    assert sanitize_path_component("test-file_name") == "test-file_name"


def test_invalid_characters_replaced() -> None:
    """Test that invalid characters are replaced with underscores."""
    assert sanitize_path_component("Episode: The Beginning") == "Episode_ The Beginning"
    assert sanitize_path_component("A/B Testing") == "A_B Testing"


def test_truncation_at_word_boundary() -> None:
    """Test that long strings are truncated at word boundaries."""
    long_title = "This is a very long episode title that exceeds the limit"
    result = sanitize_path_component(long_title)
    
    assert len(result) <= 30
    # Should truncate at word boundary
    assert result == "This is a very long episode"


def test_custom_max_length() -> None:
    """Test custom max_length parameter."""
    result = sanitize_path_component("Hello World Test", max_length=10)
    assert len(result) <= 10


def test_unicode_preserved() -> None:
    """Test that Unicode characters are preserved."""
    assert sanitize_path_component("Café") == "Café"
    assert sanitize_path_component("日本語") == "日本語"
