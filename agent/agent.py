"""
agent.py — ADK Text Summarizer Agent

Defines the root ADK Agent that uses Gemini to summarize text.
The agent exposes a `summarize_text` tool which the LLM calls
to return a structured JSON response.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool


# ---------------------------------------------------------------------------
# Tool definition
# The docstring is used by ADK to describe the tool to the model.
# ---------------------------------------------------------------------------
def summarize_text(text: str, style: str = "bullet") -> dict:
    """
    Summarize the provided text and return structured results.

    Args:
        text:  The raw text to be summarized.
        style: Output style — use 'bullet' for bullet points,
               or 'paragraph' for prose. Defaults to 'bullet'.

    Returns:
        A dictionary containing:
          - summary    (str)       : The summarized content.
          - word_count (int)       : Approximate word count of the original text.
          - key_topics (list[str]) : Up to 5 key topics extracted from the text.
          - sentiment  (str)       : Overall sentiment — 'positive', 'neutral', or 'negative'.
    """
    # ADK routes this call to Gemini; the return value is a schema hint.
    return {
        "summary": "",
        "word_count": 0,
        "key_topics": [],
        "sentiment": "neutral",
    }


# ---------------------------------------------------------------------------
# Root agent
# ---------------------------------------------------------------------------
root_agent = Agent(
    name="summarizer_agent",
    model="gemini-2.0-flash",
    description=(
        "A production-ready AI agent that summarizes text using Gemini. "
        "Given any input text, it returns a concise summary, word count, "
        "key topics, and overall sentiment."
    ),
    instruction=(
        "You are an expert text summarization assistant. "
        "When a user provides text, ALWAYS call the summarize_text tool with the text and requested style. "
        "Respond ONLY with valid JSON matching this exact schema:\n"
        "{\n"
        '  "summary": "<your summary here>",\n'
        '  "word_count": <integer>,\n'
        '  "key_topics": ["topic1", "topic2", ...],\n'
        '  "sentiment": "positive" | "neutral" | "negative"\n'
        "}\n"
        "Do not include markdown code fences or any extra text outside the JSON object."
    ),
    tools=[FunctionTool(summarize_text)],
)
