"""Claude API client wrapper."""

import anthropic

from podtext.config.manager import Config


class ClaudeError(Exception):
    """Exception raised for Claude API errors."""

    pass


class ClaudeClient:
    """Wrapper for the Anthropic Claude API."""

    def __init__(self, config: Config):
        """Initialize the Claude client.

        Args:
            config: Application configuration with API key and model settings
        """
        self.config = config
        api_key = config.get_api_key()

        if not api_key:
            raise ClaudeError(
                "No Claude API key configured. "
                "Set ANTHROPIC_API_KEY environment variable or configure in config.toml"
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = config.claude_model

    def execute_prompt(
        self,
        prompt: str,
        content: str,
        max_tokens: int = 4096,
    ) -> str:
        """Execute a prompt with the given content.

        Args:
            prompt: The system/instruction prompt
            content: The content to analyze
            max_tokens: Maximum tokens in response

        Returns:
            The model's response text

        Raises:
            ClaudeError: If the API request fails
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n---\n\n{content}",
                    }
                ],
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text

            return ""

        except anthropic.AuthenticationError as e:
            raise ClaudeError(f"Authentication failed: {e}") from e
        except anthropic.RateLimitError as e:
            raise ClaudeError(f"Rate limit exceeded: {e}") from e
        except anthropic.APIError as e:
            raise ClaudeError(f"API error: {e}") from e

    def analyze_summary(self, prompt: str, transcript: str) -> str:
        """Generate a summary of the transcript.

        Args:
            prompt: The summary prompt
            transcript: The transcript text

        Returns:
            Summary text
        """
        return self.execute_prompt(prompt, transcript)

    def analyze_topics(self, prompt: str, transcript: str) -> list[str]:
        """Extract topics from the transcript.

        Args:
            prompt: The topics prompt
            transcript: The transcript text

        Returns:
            List of topic strings
        """
        response = self.execute_prompt(prompt, transcript)
        return self._parse_bullet_list(response)

    def analyze_keywords(self, prompt: str, transcript: str) -> list[str]:
        """Extract keywords from the transcript.

        Args:
            prompt: The keywords prompt
            transcript: The transcript text

        Returns:
            List of keyword strings
        """
        response = self.execute_prompt(prompt, transcript)
        return self._parse_comma_list(response)

    def detect_advertising(self, prompt: str, transcript: str) -> str:
        """Detect advertising segments in the transcript.

        Args:
            prompt: The advertising detection prompt
            transcript: The transcript text

        Returns:
            Raw response describing detected ads
        """
        return self.execute_prompt(prompt, transcript)

    def _parse_bullet_list(self, text: str) -> list[str]:
        """Parse a bullet-point list from text."""
        import re

        items = []
        for line in text.split("\n"):
            line = line.strip()
            # Skip empty lines and headers
            if not line or line.startswith("#"):
                continue

            item = None
            # Handle bullet points (-, *, •) but not ** which is bold
            if re.match(r"^[-•]\s", line) or (line.startswith("* ") and not line.startswith("**")):
                item = re.sub(r"^[-*•]\s*", "", line).strip()
            # Handle numbered lists (1. item, 2. item, 1) item)
            elif re.match(r"^\d+[.)]\s", line):
                item = re.sub(r"^\d+[.)]\s*", "", line).strip()

            if item:
                # Remove markdown bold/italic markers
                item = self._strip_markdown(item)
                if item:
                    items.append(item)
        return items

    def _parse_comma_list(self, text: str) -> list[str]:
        """Parse a comma-separated list from text."""
        import re

        # Split into lines and filter out headers/preamble
        lines = text.strip().split("\n")
        filtered_lines = []
        for line in lines:
            line = line.strip()
            # Skip markdown headers
            if line.startswith("#"):
                continue
            # Skip common preamble lines
            if re.match(r"^(here are|keywords?|the keywords?)[^:]*:", line, re.IGNORECASE):
                continue
            # Skip empty lines
            if not line:
                continue
            filtered_lines.append(line)

        # Check if response uses bullet points instead of commas
        bullet_lines = [ln for ln in filtered_lines if ln.startswith(("-", "*", "•"))]
        if len(bullet_lines) > len(filtered_lines) // 2:
            # Mostly bullet points, parse as bullet list
            return self._parse_bullet_list("\n".join(filtered_lines))

        # Handle multi-line responses by joining
        text = " ".join(filtered_lines)

        # Remove markdown formatting
        text = self._strip_markdown(text)

        # Split by comma and clean up
        items = []
        for item in text.split(","):
            item = item.strip()
            # Skip items that look like headers or preamble
            if item and not item.endswith(":") and len(item) < 100:
                items.append(item)

        return items

    def _strip_markdown(self, text: str) -> str:
        """Remove common markdown formatting from text."""
        import re
        # Remove bold (**text** or __text__)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        # Remove italic (*text* or _text_)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        # Remove inline code (`text`)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        return text.strip()
