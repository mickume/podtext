# Advertisement Detection

Analyze the following transcript and identify advertising sections.

For each advertisement section found, provide:
1. The start position (character index) in the text
2. The end position (character index) in the text
3. A confidence score (0.0 to 1.0)

Only include sections with high confidence (>= 0.8) as advertisements.

Respond in JSON format:
{
  "advertisements": [
    {"start": <int>, "end": <int>, "confidence": <float>}
  ]
}

Transcript:


# Content Summary

Summarize the following podcast transcript in 2-3 paragraphs.
Focus on the main points discussed and key takeaways.

Transcript:


# Topic Extraction

List the main topics covered in the following podcast transcript.
For each topic, provide a one-sentence description.

Format your response as a JSON array of strings:
["Topic 1: description", "Topic 2: description", ...]

Transcript:


# Keyword Extraction

Extract the most important keywords from the following podcast transcript.
Focus on key names, core concepts, technologies, and broader categories.
Limit to 20 keywords maximum, prioritizing the most significant terms.

Format your response as a JSON array of strings:
["keyword1", "keyword2", ...]

Transcript:
