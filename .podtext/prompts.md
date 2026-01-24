# Advertisement Detection

Analyze the following podcast transcript and identify advertising sections.

For each advertisement section, provide:
1. The start position (character index) in the text
2. The end position (character index) in the text
3. Your confidence level (high, medium, low)

Only mark sections as advertisements if you are highly confident. These include:
- Explicit sponsor reads ("This episode is brought to you by...")
- Product promotions with promo codes
- Service endorsements with special offers

Return the results as JSON in this format:
{{"advertisements": [{{"start": 0, "end": 100, "confidence": "high"}}]}}

If no advertisements are found, return: {{"advertisements": []}}

Transcript:
{text}

# Content Summary

Summarize the following podcast transcript in 2-3 sentences.
Focus on the main topic and key takeaways.

Transcript:
{text}

# Topic Extraction

List the main topics covered in this podcast transcript.
For each topic, provide a single sentence description.
Return as a JSON array of strings.

Format: ["Topic 1: Brief description", "Topic 2: Brief description"]

Transcript:
{text}

# Keyword Extraction

Extract relevant keywords from this podcast transcript.
Include names, concepts, technologies, and important terms.
Return as a JSON array of strings, maximum 20 keywords.

Format: ["keyword1", "keyword2", "keyword3"]

Transcript:
{text}
