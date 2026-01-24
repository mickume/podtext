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
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•")):
                item = line.lstrip("-*• ").strip()
                if item:
                    items.append(item)
            elif line and not any(line.startswith(c) for c in "#123456789"):
                # Include non-list lines that aren't headers or numbered items
                items.append(line)
        return items

    def _parse_comma_list(self, text: str) -> list[str]:
        """Parse a comma-separated list from text."""
        # Handle multi-line responses by joining
        text = " ".join(text.split("\n"))
        # Split by comma and clean up
        items = [item.strip() for item in text.split(",")]
        return [item for item in items if item]
