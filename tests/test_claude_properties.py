"""Property-based tests for Claude Integration.

Feature: podtext
Tests prompt runtime loading behavior for Claude API integration.

Validates: Requirements 9.2
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from podtext.core.prompts import (
    DEFAULT_ADVERTISEMENT_DETECTION_PROMPT,
    DEFAULT_CONTENT_SUMMARY_PROMPT,
    DEFAULT_KEYWORD_EXTRACTION_PROMPT,
    DEFAULT_TOPIC_EXTRACTION_PROMPT,
    load_prompts,
)
from podtext.services.claude import (
    analyze_content,
    detect_advertisements,
)

# =============================================================================
# Strategies for generating test data
# =============================================================================


# Strategy for generating valid prompt content (non-empty strings)
# Note: The prompts parser strips whitespace, so we generate prompts that
# end with non-whitespace characters to ensure consistent comparison.
@st.composite
def _prompt_content_strategy(draw: st.DrawFn) -> str:
    """Generate valid prompt content that won't be affected by strip().

    The prompts parser strips whitespace from prompt content, so we generate
    prompts that start and end with alphanumeric characters.
    """
    # Generate a prefix (required, alphanumeric)
    prefix = draw(st.from_regex(r"[A-Za-z][A-Za-z0-9]{4,10}", fullmatch=True))

    # Generate optional middle content
    middle = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N", "P", "S"),
                whitelist_characters=" ",
            ),
            min_size=0,
            max_size=50,
        )
    )

    # Generate a suffix (required, alphanumeric) to ensure no trailing whitespace issues
    suffix = draw(st.from_regex(r"[A-Za-z0-9]{4,10}", fullmatch=True))

    return f"{prefix}{middle}{suffix}"


# Create the strategy instance
prompt_content_strategy = _prompt_content_strategy()

# Strategy for generating unique prompt identifiers
prompt_id_strategy = st.from_regex(
    r"[a-zA-Z][a-zA-Z0-9_]{5,15}",
    fullmatch=True,
)

# Strategy for generating prompt section names
section_name_strategy = st.sampled_from(
    [
        "advertisement_detection",
        "content_summary",
        "topic_extraction",
        "keyword_extraction",
    ]
)


def create_prompts_markdown(
    ad_prompt: str | None = None,
    summary_prompt: str | None = None,
    topic_prompt: str | None = None,
    keyword_prompt: str | None = None,
) -> str:
    """Create a prompts markdown file content with the given prompts.

    Args:
        ad_prompt: Advertisement detection prompt content.
        summary_prompt: Content summary prompt content.
        topic_prompt: Topic extraction prompt content.
        keyword_prompt: Keyword extraction prompt content.

    Returns:
        Markdown-formatted string with all prompts.
    """
    sections = []

    if ad_prompt is not None:
        sections.append(f"# Advertisement Detection\n\n{ad_prompt}")

    if summary_prompt is not None:
        sections.append(f"# Content Summary\n\n{summary_prompt}")

    if topic_prompt is not None:
        sections.append(f"# Topic Extraction\n\n{topic_prompt}")

    if keyword_prompt is not None:
        sections.append(f"# Keyword Extraction\n\n{keyword_prompt}")

    return "\n\n".join(sections)


# =============================================================================
# Property 13: Prompt Runtime Loading
# =============================================================================


class TestPromptRuntimeLoading:
    """Property 13: Prompt Runtime Loading

    Feature: podtext, Property 13: Prompt Runtime Loading

    For any modification to the prompts markdown file, subsequent Claude API calls
    SHALL use the updated prompt content.

    **Validates: Requirements 9.2**
    """

    @settings(max_examples=100)
    @given(
        initial_prompt=prompt_content_strategy,
        updated_prompt=prompt_content_strategy,
    )
    def test_detect_advertisements_uses_updated_prompts(
        self,
        initial_prompt: str,
        updated_prompt: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - detect_advertisements

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any modification to the prompts markdown file, subsequent
        detect_advertisements calls SHALL use the updated prompt content.

        **Validates: Requirements 9.2**
        """
        # Ensure prompts are different and not substrings of each other
        assume(initial_prompt.strip() != updated_prompt.strip())
        assume(initial_prompt not in updated_prompt)
        assume(updated_prompt not in initial_prompt)

        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            # Write initial prompts file
            local_path.write_text(
                create_prompts_markdown(
                    ad_prompt=initial_prompt,
                    summary_prompt="Summary prompt",
                    topic_prompt="Topic prompt",
                    keyword_prompt="Keyword prompt",
                )
            )

            # Track API calls to verify prompt content
            api_calls: list[str] = []

            with patch("podtext.services.claude._create_client") as mock_create_client:
                mock_client = MagicMock()
                mock_create_client.return_value = mock_client

                def capture_call(*args: Any, **kwargs: Any) -> MagicMock:
                    messages = kwargs.get("messages", [])
                    if messages:
                        api_calls.append(messages[0]["content"])
                    return MagicMock(content=[MagicMock(text='{"advertisements": []}')])

                mock_client.messages.create.side_effect = capture_call

                # First call - should use initial prompt
                prompts1 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                detect_advertisements(
                    text="Test transcript",
                    api_key="test-key",
                    prompts=prompts1,
                )

                # Verify initial prompt was used
                assert len(api_calls) == 1
                assert initial_prompt in api_calls[0], (
                    f"Initial prompt '{initial_prompt[:50]}...' should be in API call"
                )

                # Update the prompts file
                local_path.write_text(
                    create_prompts_markdown(
                        ad_prompt=updated_prompt,
                        summary_prompt="Summary prompt",
                        topic_prompt="Topic prompt",
                        keyword_prompt="Keyword prompt",
                    )
                )

                # Second call - should use updated prompt
                prompts2 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                detect_advertisements(
                    text="Test transcript",
                    api_key="test-key",
                    prompts=prompts2,
                )

                # Property: Subsequent calls SHALL use updated prompt content
                assert len(api_calls) == 2
                assert updated_prompt in api_calls[1], (
                    f"Updated prompt '{updated_prompt[:50]}...' should be in API call"
                )
                assert initial_prompt not in api_calls[1], (
                    "Initial prompt should NOT be in second API call"
                )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        initial_summary=prompt_content_strategy,
        updated_summary=prompt_content_strategy,
    )
    def test_analyze_content_uses_updated_summary_prompt(
        self,
        initial_summary: str,
        updated_summary: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - analyze_content summary

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any modification to the content summary prompt, subsequent
        analyze_content calls SHALL use the updated prompt content.

        **Validates: Requirements 9.2**
        """
        # Ensure prompts are different
        assume(initial_summary.strip() != updated_summary.strip())

        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            # Write initial prompts file
            local_path.write_text(
                create_prompts_markdown(
                    ad_prompt="Ad prompt",
                    summary_prompt=initial_summary,
                    topic_prompt="Topic prompt",
                    keyword_prompt="Keyword prompt",
                )
            )

            # Track API calls to verify prompt content
            summary_calls: list[str] = []

            with patch("podtext.services.claude._create_client") as mock_create_client:
                mock_client = MagicMock()
                mock_create_client.return_value = mock_client

                call_count = [0]

                def capture_call(*args: Any, **kwargs: Any) -> MagicMock:
                    messages = kwargs.get("messages", [])
                    call_count[0] += 1

                    # First call in analyze_content is summary
                    if call_count[0] % 4 == 1 and messages:
                        summary_calls.append(messages[0]["content"])

                    # Return appropriate mock responses
                    return MagicMock(content=[MagicMock(text="Summary response")])

                mock_client.messages.create.side_effect = capture_call

                # First call - should use initial prompt
                prompts1 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                analyze_content(
                    text="Test transcript",
                    api_key="test-key",
                    prompts=prompts1,
                    warn_on_unavailable=False,
                )

                # Verify initial prompt was used
                assert len(summary_calls) == 1
                assert initial_summary in summary_calls[0], (
                    "Initial summary prompt should be in first API call"
                )

                # Update the prompts file
                local_path.write_text(
                    create_prompts_markdown(
                        ad_prompt="Ad prompt",
                        summary_prompt=updated_summary,
                        topic_prompt="Topic prompt",
                        keyword_prompt="Keyword prompt",
                    )
                )

                # Second call - should use updated prompt
                prompts2 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                analyze_content(
                    text="Test transcript",
                    api_key="test-key",
                    prompts=prompts2,
                    warn_on_unavailable=False,
                )

                # Property: Subsequent calls SHALL use updated prompt content
                assert len(summary_calls) == 2
                assert updated_summary in summary_calls[1], (
                    "Updated summary prompt should be in second API call"
                )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        prompt_v1=prompt_content_strategy,
        prompt_v2=prompt_content_strategy,
        prompt_v3=prompt_content_strategy,
    )
    def test_multiple_prompt_updates_all_reflected(
        self,
        prompt_v1: str,
        prompt_v2: str,
        prompt_v3: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - Multiple Updates

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any sequence of modifications to the prompts file, each subsequent
        Claude API call SHALL use the most recently updated prompt content.

        **Validates: Requirements 9.2**
        """
        # Ensure all prompts are different
        assume(prompt_v1.strip() != prompt_v2.strip())
        assume(prompt_v2.strip() != prompt_v3.strip())
        assume(prompt_v1.strip() != prompt_v3.strip())

        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            api_calls: list[str] = []

            with patch("podtext.services.claude._create_client") as mock_create_client:
                mock_client = MagicMock()
                mock_create_client.return_value = mock_client

                def capture_call(*args: Any, **kwargs: Any) -> MagicMock:
                    messages = kwargs.get("messages", [])
                    if messages:
                        api_calls.append(messages[0]["content"])
                    return MagicMock(content=[MagicMock(text='{"advertisements": []}')])

                mock_client.messages.create.side_effect = capture_call

                # Version 1
                local_path.write_text(create_prompts_markdown(ad_prompt=prompt_v1))
                prompts1 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                detect_advertisements(
                    text="Test",
                    api_key="test-key",
                    prompts=prompts1,
                )

                # Version 2
                local_path.write_text(create_prompts_markdown(ad_prompt=prompt_v2))
                prompts2 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                detect_advertisements(
                    text="Test",
                    api_key="test-key",
                    prompts=prompts2,
                )

                # Version 3
                local_path.write_text(create_prompts_markdown(ad_prompt=prompt_v3))
                prompts3 = load_prompts(
                    local_path=local_path,
                    global_path=global_path,
                    warn_on_fallback=False,
                )
                detect_advertisements(
                    text="Test",
                    api_key="test-key",
                    prompts=prompts3,
                )

                # Property: Each call SHALL use the corresponding version
                assert len(api_calls) == 3
                assert prompt_v1 in api_calls[0], "First call should use v1 prompt"
                assert prompt_v2 in api_calls[1], "Second call should use v2 prompt"
                assert prompt_v3 in api_calls[2], "Third call should use v3 prompt"
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        initial_prompt=prompt_content_strategy,
        updated_prompt=prompt_content_strategy,
    )
    def test_load_prompts_reads_file_each_time(
        self,
        initial_prompt: str,
        updated_prompt: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - No Caching

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any modification to the prompts file, load_prompts SHALL return
        the updated content without caching previous values.

        **Validates: Requirements 9.2**
        """
        # Ensure prompts are different
        assume(initial_prompt.strip() != updated_prompt.strip())

        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            # Write initial prompts
            local_path.write_text(create_prompts_markdown(ad_prompt=initial_prompt))

            # Load prompts - should get initial content
            prompts1 = load_prompts(
                local_path=local_path,
                global_path=global_path,
                warn_on_fallback=False,
            )
            assert prompts1.advertisement_detection == initial_prompt, (
                "First load should return initial prompt"
            )

            # Update the file
            local_path.write_text(create_prompts_markdown(ad_prompt=updated_prompt))

            # Load prompts again - should get updated content
            prompts2 = load_prompts(
                local_path=local_path,
                global_path=global_path,
                warn_on_fallback=False,
            )

            # Property: load_prompts SHALL return updated content
            assert prompts2.advertisement_detection == updated_prompt, (
                f"Second load should return updated prompt '{updated_prompt[:50]}...', "
                f"but got '{prompts2.advertisement_detection[:50]}...'"
            )

            # Verify the prompts are different
            assert prompts1.advertisement_detection != prompts2.advertisement_detection, (
                "Prompts should be different after file update"
            )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        ad_prompt=prompt_content_strategy,
        summary_prompt=prompt_content_strategy,
        topic_prompt=prompt_content_strategy,
        keyword_prompt=prompt_content_strategy,
    )
    def test_all_prompt_sections_loaded_at_runtime(
        self,
        ad_prompt: str,
        summary_prompt: str,
        topic_prompt: str,
        keyword_prompt: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - All Sections

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any prompts file with all sections, load_prompts SHALL load
        all prompt sections at runtime.

        **Validates: Requirements 9.2**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            # Write prompts file with all sections
            local_path.write_text(
                create_prompts_markdown(
                    ad_prompt=ad_prompt,
                    summary_prompt=summary_prompt,
                    topic_prompt=topic_prompt,
                    keyword_prompt=keyword_prompt,
                )
            )

            # Load prompts
            prompts = load_prompts(
                local_path=local_path,
                global_path=global_path,
                warn_on_fallback=False,
            )

            # Property: All sections SHALL be loaded from file
            assert prompts.advertisement_detection == ad_prompt, (
                "Advertisement detection prompt should match file content"
            )
            assert prompts.content_summary == summary_prompt, (
                "Content summary prompt should match file content"
            )
            assert prompts.topic_extraction == topic_prompt, (
                "Topic extraction prompt should match file content"
            )
            assert prompts.keyword_extraction == keyword_prompt, (
                "Keyword extraction prompt should match file content"
            )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        initial_prompt=prompt_content_strategy,
    )
    def test_deleted_file_falls_back_to_defaults(
        self,
        initial_prompt: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - File Deletion

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any prompts file that is deleted, subsequent load_prompts calls
        SHALL fall back to built-in defaults.

        **Validates: Requirements 9.2, 9.3**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            # Write initial prompts file
            local_path.write_text(create_prompts_markdown(ad_prompt=initial_prompt))

            # Load prompts - should get custom content
            prompts1 = load_prompts(
                local_path=local_path,
                global_path=global_path,
                warn_on_fallback=False,
            )
            assert prompts1.advertisement_detection == initial_prompt

            # Delete the file
            local_path.unlink()

            # Load prompts again - should fall back to defaults
            prompts2 = load_prompts(
                local_path=local_path,
                global_path=global_path,
                warn_on_fallback=False,
            )

            # Property: After deletion, SHALL use built-in defaults
            assert prompts2.advertisement_detection == DEFAULT_ADVERTISEMENT_DETECTION_PROMPT, (
                "After file deletion, should use default advertisement detection prompt"
            )
            assert prompts2.content_summary == DEFAULT_CONTENT_SUMMARY_PROMPT, (
                "After file deletion, should use default content summary prompt"
            )
            assert prompts2.topic_extraction == DEFAULT_TOPIC_EXTRACTION_PROMPT, (
                "After file deletion, should use default topic extraction prompt"
            )
            assert prompts2.keyword_extraction == DEFAULT_KEYWORD_EXTRACTION_PROMPT, (
                "After file deletion, should use default keyword extraction prompt"
            )
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)

    @settings(max_examples=100)
    @given(
        prompt_content=prompt_content_strategy,
        section=section_name_strategy,
    )
    def test_partial_update_reflects_in_api_calls(
        self,
        prompt_content: str,
        section: str,
    ) -> None:
        """Property 13: Prompt Runtime Loading - Partial Updates

        Feature: podtext, Property 13: Prompt Runtime Loading

        For any modification to a single prompt section, subsequent Claude API
        calls using that section SHALL use the updated content.

        **Validates: Requirements 9.2**
        """
        base_dir = Path(tempfile.mkdtemp())
        unique_id = str(uuid.uuid4())[:8]
        prompts_dir = base_dir / f"prompts_{unique_id}"
        prompts_dir.mkdir(parents=True)

        local_path = prompts_dir / "prompts.md"
        global_path = prompts_dir / "global_prompts.md"

        try:
            # Create prompts with the specified section updated
            kwargs = {
                "ad_prompt": "Default ad"
                if section != "advertisement_detection"
                else prompt_content,
                "summary_prompt": "Default summary"
                if section != "content_summary"
                else prompt_content,
                "topic_prompt": "Default topic"
                if section != "topic_extraction"
                else prompt_content,
                "keyword_prompt": "Default keyword"
                if section != "keyword_extraction"
                else prompt_content,
            }

            local_path.write_text(create_prompts_markdown(**kwargs))

            # Load prompts
            prompts = load_prompts(
                local_path=local_path,
                global_path=global_path,
                warn_on_fallback=False,
            )

            # Property: The updated section SHALL contain the new content
            if section == "advertisement_detection":
                assert prompts.advertisement_detection == prompt_content
            elif section == "content_summary":
                assert prompts.content_summary == prompt_content
            elif section == "topic_extraction":
                assert prompts.topic_extraction == prompt_content
            elif section == "keyword_extraction":
                assert prompts.keyword_extraction == prompt_content
        finally:
            import shutil

            shutil.rmtree(base_dir, ignore_errors=True)
