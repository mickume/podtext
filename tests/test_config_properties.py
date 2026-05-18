"""Property-based tests for the Config Manager.

Feature: podtext
Tests configuration loading priority and environment variable precedence.

Validates: Requirements 8.1, 8.2, 8.5
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from podtext.core.config import (
    VALID_WHISPER_MODELS,
    load_config,
)

# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for valid whisper model names
whisper_model_strategy = st.sampled_from(list(VALID_WHISPER_MODELS))

# TOML-safe printable ASCII characters (excluding control chars and problematic chars)
# TOML basic strings allow: printable ASCII except backslash and quote (which need escaping)
TOML_SAFE_CHARS = "".join(chr(c) for c in range(32, 127) if chr(c) not in '\\"\x7f')

# Strategy for TOML-safe strings (for API keys)
toml_safe_string_strategy = st.text(
    alphabet=TOML_SAFE_CHARS,
    min_size=0,
    max_size=50,
)

# Strategy for non-empty TOML-safe strings
non_empty_string_strategy = st.text(
    alphabet=TOML_SAFE_CHARS,
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")

# Strategy for valid directory paths (simple alphanumeric with slashes)
path_string_strategy = st.from_regex(
    r"[a-zA-Z0-9_/.-]{1,50}",
    fullmatch=True,
).filter(lambda s: s.strip() != "" and not s.startswith("/"))


# Strategy for generating valid config dictionaries
@st.composite
def config_dict_strategy(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a valid configuration dictionary."""
    return {
        "storage": {
            "media_dir": draw(path_string_strategy),
            "output_dir": draw(path_string_strategy),
            "temp_storage": draw(st.booleans()),
        },
        "whisper": {
            "model": draw(whisper_model_strategy),
        },
    }


def dict_to_toml(config_dict: dict[str, Any]) -> str:
    """Convert a configuration dictionary to TOML format.

    Simple TOML serialization for test configs.
    """
    lines = []
    for section, values in config_dict.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            if isinstance(value, bool):
                lines.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, str):
                # Escape any special characters in strings
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key} = "{escaped}"')
            else:
                lines.append(f"{key} = {value}")
        lines.append("")
    return "\n".join(lines)


def create_temp_config_dirs() -> tuple[Path, Path, Path]:
    """Create unique temporary directories for config files.

    Returns:
        Tuple of (base_dir, local_path, global_path)
    """
    base_dir = Path(tempfile.mkdtemp())
    unique_id = str(uuid.uuid4())[:8]
    local_dir = base_dir / f"local_{unique_id}"
    global_dir = base_dir / f"global_{unique_id}"
    local_dir.mkdir(parents=True)
    global_dir.mkdir(parents=True)
    return base_dir, local_dir / "config", global_dir / "config"


# =============================================================================
# Property 11: Config Loading Priority
# =============================================================================


class TestConfigLoadingPriority:
    """Property 11: Config Loading Priority

    Feature: podtext, Property 11: Config Loading Priority

    For any configuration key present in both local and global config files,
    the value from the local config file SHALL be used.

    **Validates: Requirements 8.1, 8.2**
    """

    @settings(max_examples=100)
    @given(
        global_config=config_dict_strategy(),
        local_config=config_dict_strategy(),
    )
    def test_local_config_overrides_global_for_all_keys(
        self,
        global_config: dict[str, Any],
        local_config: dict[str, Any],
    ) -> None:
        """Property 11: Config Loading Priority

        Feature: podtext, Property 11: Config Loading Priority

        For any configuration key present in both local and global config files,
        the value from the local config file SHALL be used.

        **Validates: Requirements 8.1, 8.2**
        """
        # Ensure env var doesn't interfere
        original_env = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            # Create unique directories for this test run
            base_dir, local_path, global_path = create_temp_config_dirs()

            try:
                # Write both config files
                global_path.write_text(dict_to_toml(global_config))
                local_path.write_text(dict_to_toml(local_config))

                # Load the merged configuration
                config = load_config(
                    local_path=local_path,
                    global_path=global_path,
                    auto_create_local=False,
                )

                # Property: Local values SHALL be used for all keys present in local config
                # Check storage section
                assert config.storage.media_dir == local_config["storage"]["media_dir"], (
                    f"Local media_dir '{local_config['storage']['media_dir']}' "
                    f"should override global '{global_config['storage']['media_dir']}', "
                    f"but got '{config.storage.media_dir}'"
                )
                assert config.storage.output_dir == local_config["storage"]["output_dir"], (
                    f"Local output_dir '{local_config['storage']['output_dir']}' "
                    f"should override global '{global_config['storage']['output_dir']}', "
                    f"but got '{config.storage.output_dir}'"
                )
                assert config.storage.temp_storage == local_config["storage"]["temp_storage"], (
                    f"Local temp_storage '{local_config['storage']['temp_storage']}' "
                    f"should override global '{global_config['storage']['temp_storage']}', "
                    f"but got '{config.storage.temp_storage}'"
                )

                # Check whisper section
                assert config.whisper.model == local_config["whisper"]["model"], (
                    f"Local whisper model '{local_config['whisper']['model']}' "
                    f"should override global '{global_config['whisper']['model']}', "
                    f"but got '{config.whisper.model}'"
                )
            finally:
                # Cleanup temp directory
                import shutil

                shutil.rmtree(base_dir, ignore_errors=True)
        finally:
            if original_env is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_env

    @settings(max_examples=100)
    @given(
        global_value=whisper_model_strategy,
        local_value=whisper_model_strategy,
    )
    def test_local_whisper_model_overrides_global(
        self,
        global_value: str,
        local_value: str,
    ) -> None:
        """Property 11: Config Loading Priority - Whisper Model

        Feature: podtext, Property 11: Config Loading Priority

        For the whisper.model key present in both local and global config files,
        the value from the local config file SHALL be used.

        **Validates: Requirements 8.1, 8.2**
        """
        # Ensure env var doesn't interfere
        original_env = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            base_dir, local_path, global_path = create_temp_config_dirs()

            try:
                global_path.write_text(f'[whisper]\nmodel = "{global_value}"')
                local_path.write_text(f'[whisper]\nmodel = "{local_value}"')

                config = load_config(
                    local_path=local_path,
                    global_path=global_path,
                    auto_create_local=False,
                )

                # Property: Local whisper model SHALL be used
                assert config.whisper.model == local_value, (
                    f"Local model '{local_value}' should override global '{global_value}', "
                    f"but got '{config.whisper.model}'"
                )
            finally:
                import shutil

                shutil.rmtree(base_dir, ignore_errors=True)
        finally:
            if original_env is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_env

    @settings(max_examples=100)
    @given(
        global_value=st.booleans(),
        local_value=st.booleans(),
    )
    def test_local_temp_storage_overrides_global(
        self,
        global_value: bool,
        local_value: bool,
    ) -> None:
        """Property 11: Config Loading Priority - Temp Storage

        Feature: podtext, Property 11: Config Loading Priority

        For the storage.temp_storage key present in both local and global config files,
        the value from the local config file SHALL be used.

        **Validates: Requirements 8.1, 8.2**
        """
        original_env = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            base_dir, local_path, global_path = create_temp_config_dirs()

            try:
                global_path.write_text(f"[storage]\ntemp_storage = {str(global_value).lower()}")
                local_path.write_text(f"[storage]\ntemp_storage = {str(local_value).lower()}")

                config = load_config(
                    local_path=local_path,
                    global_path=global_path,
                    auto_create_local=False,
                )

                # Property: Local temp_storage SHALL be used
                assert config.storage.temp_storage == local_value, (
                    f"Local temp_storage '{local_value}' should override global '{global_value}', "
                    f"but got '{config.storage.temp_storage}'"
                )
            finally:
                import shutil

                shutil.rmtree(base_dir, ignore_errors=True)
        finally:
            if original_env is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_env


# =============================================================================
# Property 12: Environment Variable Precedence
# =============================================================================


class TestEnvironmentVariableApiKey:
    """Property 12: Environment Variable API Key

    Feature: podtext, Property 12: Environment Variable API Key

    The API key SHALL only be read from the ANTHROPIC_API_KEY environment variable.

    **Validates: Requirements 8.5**
    """

    @settings(max_examples=100)
    @given(
        env_value=non_empty_string_strategy,
    )
    def test_env_var_provides_api_key(
        self,
        env_value: str,
    ) -> None:
        """Property 12: Environment Variable API Key

        For any ANTHROPIC_API_KEY environment variable value V,
        get_anthropic_key() SHALL return V.

        **Validates: Requirements 8.5**
        """
        assume(env_value.strip() != "")

        original_env = os.environ.get("ANTHROPIC_API_KEY")
        try:
            os.environ["ANTHROPIC_API_KEY"] = env_value

            config = load_config(auto_create_local=False)

            actual_key = config.get_anthropic_key()
            assert actual_key == env_value, (
                f"Environment variable value '{env_value}' should be used, "
                f"but got '{actual_key}'"
            )
        finally:
            if original_env is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_env
            elif "ANTHROPIC_API_KEY" in os.environ:
                del os.environ["ANTHROPIC_API_KEY"]

    def test_no_api_key_when_env_var_not_set(self) -> None:
        """When ANTHROPIC_API_KEY is not set, get_anthropic_key() SHALL return empty string.

        **Validates: Requirements 8.5**
        """
        original_env = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            config = load_config(auto_create_local=False)

            actual_key = config.get_anthropic_key()
            assert actual_key == "", (
                f"Expected empty string when env var not set, but got '{actual_key}'"
            )
        finally:
            if original_env is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_env
