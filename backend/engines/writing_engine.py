from anthropic import Anthropic
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# AI TELL-TALE PHRASES TO AVOID
BANNED_PHRASES = [
    "in today's rapidly evolving",
    "in an era where",
    "let's dive into",
    "let's unpack",
    "here's the thing",
    "at the end of the day",
    "the bottom line is",
    "excited to announce",
    "thrilled to share",
    "leverage synergies",
    "game-changer",
    "best practices",
    "deep dive"
]


def _format_research_for_prompt(research_data: Optional[list]) -> str:
    """Format research data into a usable prompt section."""
    if not research_data:
        return ""

    sections = []
    for result in research_data:
        if result.get("error"):
            continue

        source_name = result.get("source_name", "Unknown source")
        url = result.get("url", "")
        summary = result.get("summary", "")
        facts = result.get("extracted_facts", [])

        if not facts and not summary:
            continue

        section = f"\n--- SOURCE: {source_name} ({url}) ---\n"
        if summary:
            section += f"Summary: {summary}\n"

        if facts:
            section += "Key Facts:\n"
            for fact in facts:
                fact_text = fact.get("fact", "")
                fact_type = fact.get("type", "finding")
                citation = fact.get("citation_text", f"According to {source_name}")
                section += f"  - [{fact_type}] {fact_text}\n    Citation: {citation}\n"

        sections.append(section)

    if not sections:
        return ""

    return "\n\nRESEARCH DATA FROM PROVIDED URLS:\n" + "\n".join(sections) + "\n"


def _format_data_sources_for_prompt(data_sources: Optional[list]) -> str:
    """Format data sources into a prompt section."""
    if not data_sources:
        return ""

    source_type_labels = {
        "personal": "Personal knowledge/experience",
        "client": "Client data (confidential)",
        "industry_report": "Industry report",
        "web_source": "Web source",
        "illustrative": "Illustrative/example data (NOT real)"
    }

    sections = []
    for source in data_sources:
        data_point = source.get("dataPoint", "")
        value = source.get("value", "")
        source_type = source.get("sourceType", "personal")
        description = source.get("sourceDescription", "")

        type_label = source_type_labels.get(source_type, source_type)

        line = f"  - {data_point}: {value}"
        line += f" (Source: {type_label}"
        if description:
            line += f" - {description}"
        line += ")"

        if source_type == "illustrative":
            line += " [WARNING: This is illustrative data, not real]"

        sections.append(line)

    if not sections:
        return ""

    return "\n\nDATA SOURCES PROVIDED:\n" + "\n".join(sections) + "\n"


def draft_linkedin_post(
    raw_idea: str,
    author: str,
    research_data: Optional[list] = None,
    data_sources: Optional[list] = None
) -> str:
    """
    Generate human-quality LinkedIn post with zero AI detection.
    Applies strict style guide to avoid AI patterns.

    Args:
        raw_idea: The raw content idea from the user
        author: The author's name
        research_data: Optional list of research results from URLs
        data_sources: Optional list of data source tracking info
    """

    # Build research section if available
    research_section = _format_research_for_prompt(research_data)
    sources_section = _format_data_sources_for_prompt(data_sources)

    # Add citation instructions if we have research
    citation_instructions = ""
    if research_data:
        citation_instructions = """
CITATION REQUIREMENTS (since research URLs were provided):
- When using facts from the research, cite the source naturally
- Use formats like: "According to [source]..." or "A recent [source] report found..."
- Don't over-cite - 1-2 citations is enough for a LinkedIn post
- Make citations feel natural, not academic
- If a fact seems particularly strong, attribute it
"""

    # Add warning about illustrative data
    illustrative_warning = ""
    if data_sources:
        has_illustrative = any(s.get("sourceType") == "illustrative" for s in data_sources)
        if has_illustrative:
            illustrative_warning = """
WARNING: Some data is marked as ILLUSTRATIVE (not real).
- Do NOT present illustrative data as fact
- If using illustrative data, frame it appropriately: "For example, if costs dropped from X to Y..."
- Or simply use the numbers as a realistic scenario without claiming they're real
"""

    style_guide = f"""You are drafting a LinkedIn post for {author}, a
25-year supply chain consultant at Claris AI (an AI consulting firm
specializing in retail supply chain).

RAW INSIGHT FROM {author.upper()}:
"{raw_idea}"
{research_section}{sources_section}
WRITING REQUIREMENTS:

CRITICAL - BANNED PHRASES (never use these):
- "In today's rapidly evolving..."
- "Let's dive into..."
- "Here's the thing..."
- "Excited to announce..."
- "Leverage," "synergies," "game-changer," "best practices"
- Any em-dashes (—)
- Multiple exclamation marks
- Generic conclusions like "What are your thoughts?"
{citation_instructions}{illustrative_warning}
REQUIRED STYLE:
- 600-1,100 characters total
- Short paragraphs (1-3 sentences max per paragraph)
- Mix sentence lengths: some 5 words, some 20 words
- Use contractions naturally (can't, don't, won't)
- Direct assertions: "This is broken." not "It's important to note that
this is broken."
- Specific numbers, not vague: "from 4.2 to 7.8 turns" not "significant
improvement"
- Real scenarios with details
- No hashtags
- No emojis
- End with optional question (make it genuine, not engagement bait)

STRUCTURE:
1. Hook (1-2 sentences) - Specific observation or contrarian statement
2. Problem/insight (2-4 short paragraphs) - Concrete example with real
context
3. Connection to solution (1-2 paragraphs) - How AI/better systems address
it
4. Optional close - Natural question or just end on the insight

TONE:
- Confident supply chain expert who's seen this 100 times
- Helpful but skeptical of buzzwords
- Conversational (like explaining to peer over coffee)
- Not salesy, not promotional

VALIDATION:
- Does it sound like a human expert wrote it?
- Would someone guess AI wrote this? If yes, rewrite.
- Are there any banned phrases? If yes, remove them.
- Sentence lengths varied?

Output ONLY the post text. No preamble, no explanations."""

    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        temperature=0.7,
        messages=[{"role": "user", "content": style_guide}]
    )

    draft = response.content[0].text.strip()

    # Validation: Check for banned phrases
    draft_lower = draft.lower()
    for phrase in BANNED_PHRASES:
        if phrase in draft_lower:
            # If banned phrase detected, regenerate with stronger warning
            draft = _regenerate_without_banned_phrases(raw_idea, author, phrase)
            break

    return draft


def _regenerate_without_banned_phrases(raw_idea: str, author: str,
detected_phrase: str) -> str:
    """Regenerate if banned phrase was detected"""

    regenerate_prompt = f"""The previous draft contained the banned phrase
"{detected_phrase}".

Generate a new LinkedIn post that is MORE HUMAN and LESS AI-LIKE.

Raw idea: "{raw_idea}"

Remember:
- No corporate buzzwords
- No AI-isms like "let's dive in" or "in today's"
- Direct, conversational tone
- Sounds like {author} talking naturally

Output only the post text."""

    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        temperature=0.8,  # Higher temp for more human variance
        messages=[{"role": "user", "content": regenerate_prompt}]
    )

    return response.content[0].text.strip()
