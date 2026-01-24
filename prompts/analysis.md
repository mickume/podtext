# Analysis Prompts

This file contains the LLM prompts used by podtext for transcript analysis.
You can edit these prompts to customize the analysis behavior.

## Summary Prompt

Generate a concise summary of this podcast transcript in 2-3 paragraphs.
Focus on the main themes and key takeaways.
Write in a clear, informative style.

---

## Topics Prompt

List the main topics covered in this transcript.
Each topic should be described in one sentence.
Return as a numbered list, with each topic on its own line.
Focus on substantive topics, not small talk or introductions.

---

## Keywords Prompt

Extract 5-10 relevant keywords that describe this content.
Return as a comma-separated list.
Include names of people, technologies, concepts, and themes discussed.

---

## Advertising Detection Prompt

Analyze this transcript section and determine if it is advertising content.
Advertising includes: sponsor reads, product promotions, discount codes,
"this episode is brought to you by" segments, affiliate marketing,
calls to action for products or services.

Return a JSON object with exactly this format:
{
  "is_advertising": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

Be conservative - only mark content as advertising if you are confident.
Regular discussion of products or companies as topics is NOT advertising.
