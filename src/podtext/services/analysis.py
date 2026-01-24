"""Claude API analysis service."""

import json
import re
from typing import Self

import anthropic

from podtext.core.config import Config, get_api_key, get_prompts_file
from podtext.core.errors import AnalysisError
from podtext.core.models import AdvertisingBlock, Analysis, Transcript


class PromptManager:
    """Load and manage LLM prompts from markdown file."""

    def __init__(self, prompt_file_path: str | None = None) -> None:
        """Initialize the prompt manager."""
        self.prompts: dict[str, str] = {}
        self._load_prompts(prompt_file_path)

    def _load_prompts(self, prompt_file_path: str | None = None) -> None:
        """Parse prompts from markdown file."""
        try:
            if prompt_file_path:
                from pathlib import Path

                path = Path(prompt_file_path)
            else:
                path = get_prompts_file()

            content = path.read_text()
        except FileNotFoundError:
            # Use built-in defaults
            self.prompts = self._default_prompts()
            return

        # Parse markdown sections
        current_section = ""
        current_content: list[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_section and current_content:
                    self.prompts[current_section] = "\n".join(current_content).strip()
                # Start new section
                current_section = line[3:].strip().lower().replace(" ", "_")
                current_content = []
            elif line.startswith("---"):
                # Section separator, save current
                if current_section and current_content:
                    self.prompts[current_section] = "\n".join(current_content).strip()
                current_section = ""
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section and current_content:
            self.prompts[current_section] = "\n".join(current_content).strip()

    def get(self, name: str) -> str:
        """Get prompt by section name."""
        if name not in self.prompts:
            defaults = self._default_prompts()
            return defaults.get(name, "")
        return self.prompts[name]

    @staticmethod
    def _default_prompts() -> dict[str, str]:
        """Return default prompts if file is not found."""
        return {
            "summary_prompt": """Generate a concise summary of this podcast transcript in 2-3 paragraphs.
Focus on the main themes and key takeaways.""",
            "topics_prompt": """List the main topics covered in this transcript.
Each topic should be described in one sentence.
Return as a numbered list.""",
            "keywords_prompt": """Extract 5-10 relevant keywords that describe this content.
Return as a comma-separated list.""",
            "advertising_detection_prompt": """Analyze this transcript section and determine if it is advertising content.
Advertising includes: sponsor reads, product promotions, discount codes,
"this episode is brought to you by" segments.

Return a JSON object:
{
  "is_advertising": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}""",
        }


class AnalysisService:
    """Handles Claude API analysis."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        ad_threshold: float = 0.9,
    ) -> None:
        """
        Initialize the analysis service.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            ad_threshold: Confidence threshold for advertising detection
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.ad_threshold = ad_threshold
        self.prompts = PromptManager()

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create an AnalysisService from configuration."""
        api_key = get_api_key(config)
        return cls(
            api_key=api_key,
            model=config.analysis.claude_model,
            ad_threshold=config.analysis.ad_confidence_threshold,
        )

    def analyze(self, transcript: Transcript) -> Analysis:
        """
        Perform full analysis on transcript.

        Args:
            transcript: Transcript to analyze

        Returns:
            Analysis with summary, topics, keywords, and advertising blocks

        Raises:
            AnalysisError: If analysis fails
        """
        full_text = transcript.full_text

        # Run analyses (could be parallelized in future)
        summary = self._generate_summary(full_text)
        topics = self._extract_topics(full_text)
        keywords = self._extract_keywords(full_text)
        advertising_blocks = self._detect_advertising(transcript)

        return Analysis(
            summary=summary,
            topics=topics,
            keywords=keywords,
            advertising_blocks=advertising_blocks,
        )

    def _generate_summary(self, text: str) -> str:
        """Generate a summary of the transcript."""
        prompt = self.prompts.get("summary_prompt")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nTranscript:\n{text[:50000]}",  # Limit input
                    }
                ],
            )
            return response.content[0].text  # type: ignore[union-attr]
        except anthropic.APIError as e:
            raise AnalysisError(f"Failed to generate summary: {e}") from e

    def _extract_topics(self, text: str) -> list[str]:
        """Extract main topics from the transcript."""
        prompt = self.prompts.get("topics_prompt")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nTranscript:\n{text[:50000]}",
                    }
                ],
            )
            # Parse numbered list
            result = response.content[0].text  # type: ignore[union-attr]
            topics = []
            for line in result.split("\n"):
                line = line.strip()
                # Remove numbering (1., 1), etc.)
                cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
                if cleaned:
                    topics.append(cleaned)
            return topics
        except anthropic.APIError as e:
            raise AnalysisError(f"Failed to extract topics: {e}") from e

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from the transcript."""
        prompt = self.prompts.get("keywords_prompt")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nTranscript:\n{text[:50000]}",
                    }
                ],
            )
            result = response.content[0].text  # type: ignore[union-attr]
            # Parse comma-separated list
            keywords = [k.strip() for k in result.split(",") if k.strip()]
            return keywords
        except anthropic.APIError as e:
            raise AnalysisError(f"Failed to extract keywords: {e}") from e

    def _detect_advertising(self, transcript: Transcript) -> list[AdvertisingBlock]:
        """
        Detect advertising sections in the transcript.

        Analyzes transcript in chunks to identify sponsor reads
        and promotional content.
        """
        prompt = self.prompts.get("advertising_detection_prompt")
        blocks: list[AdvertisingBlock] = []

        # Analyze in chunks of segments
        chunk_size = 10
        for i in range(0, len(transcript.segments), chunk_size):
            chunk = transcript.segments[i : i + chunk_size]
            chunk_text = " ".join(s.text for s in chunk)

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=256,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{prompt}\n\nText:\n{chunk_text}",
                        }
                    ],
                )
                result = response.content[0].text  # type: ignore[union-attr]

                # Parse JSON response
                try:
                    # Extract JSON from response
                    json_match = re.search(r"\{.*\}", result, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        if data.get("is_advertising") and data.get(
                            "confidence", 0
                        ) >= self.ad_threshold:
                            blocks.append(
                                AdvertisingBlock(
                                    start_index=i,
                                    end_index=i + len(chunk) - 1,
                                    confidence=data.get("confidence", 0.9),
                                )
                            )
                except json.JSONDecodeError:
                    pass  # Skip if can't parse response

            except anthropic.APIError:
                pass  # Skip chunk on API error

        return blocks
