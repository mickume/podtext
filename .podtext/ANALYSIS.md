# Podcast Analysis Prompts

This file contains the prompts used by podtext for AI-powered analysis.
You can customize these prompts to change how the analysis works.

## Summary Prompt

Generate a concise summary of this podcast transcript in 2-3 paragraphs.
Focus on the main themes, key insights, and notable discussions.
Write in a neutral, informative tone.

## Topics Prompt

List the main topics discussed in this podcast episode.
Provide each topic as a single sentence that captures its essence.
Return the topics as a bullet-point list.
Aim for 3-7 topics depending on episode content.

## Keywords Prompt

Extract relevant keywords from this podcast transcript.
Include names of people, organizations, products, concepts, and themes discussed.
Return keywords as a comma-separated list.
Aim for 10-20 keywords that would help with categorization and search.

## Advertising Detection Prompt

Analyze this podcast transcript and identify any advertising or sponsored content segments.
Look for:
- Host-read advertisements
- Sponsor mentions and endorsements
- Mid-roll ad segments
- Product promotions that are clearly paid content

For each advertising segment found, provide:
1. The approximate start and end of the segment (by quoting the first and last few words)
2. The advertiser or product being promoted
3. Your confidence level (high, medium, low)

Only flag segments you are confident are advertisements, not organic product discussions.
