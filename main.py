"""
main.py — FastAPI HTTP server for the ADK Summarizer Agent.

Endpoints:
  GET  /           → Health check
  GET  /agent-card → A2A-compatible JSON agent card
  POST /summarize  → Run the summarization agent
"""

import json
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agent.agent import root_agent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK session service (stateless per request — safe for Cloud Run)
# ---------------------------------------------------------------------------
session_service = InMemorySessionService()
APP_NAME = "summarizer_agent_app"


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 ADK Summarizer Agent starting up…")
    yield
    logger.info("🛑 ADK Summarizer Agent shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Gemini ADK Text Summarizer Agent",
    description=(
        "A serverless AI agent built with Google ADK + Gemini 2.0 Flash. "
        "Summarizes text via a simple HTTP POST endpoint."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=10, description="The text to summarize.")
    style: str = Field(
        "bullet",
        description="Summary style: 'bullet' for bullet points, 'paragraph' for prose.",
        pattern="^(bullet|paragraph)$",
    )
    user_id: str = Field("anonymous", description="Optional user identifier.")
    session_id: str = Field("session-001", description="Optional session identifier.")


class SummarizeResponse(BaseModel):
    summary: str
    word_count: int
    key_topics: list[str]
    sentiment: str
    model: str = "gemini-2.0-flash"
    style: str


class AgentCard(BaseModel):
    name: str
    description: str
    version: str
    endpoint: str
    capabilities: list[str]
    input_schema: dict
    output_schema: dict


# ---------------------------------------------------------------------------
# Helper: run ADK agent and return raw text
# ---------------------------------------------------------------------------
async def run_agent(user_id: str, session_id: str, prompt: str) -> str:
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    user_message = Content(role="user", parts=[Part(text=prompt)])

    raw_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    raw_text += part.text

    return raw_text.strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def health_check():
    """Liveness/readiness probe for Cloud Run."""
    return {
        "status": "ok",
        "agent": "summarizer_agent",
        "model": "gemini-2.0-flash",
        "version": "1.0.0",
    }


@app.get("/agent-card", response_model=AgentCard, tags=["A2A"])
async def agent_card(request: Request):
    """
    A2A-compatible Agent Card — describes this agent's capabilities
    so other ADK agents can use it as a sub-agent.
    """
    base_url = str(request.base_url).rstrip("/")
    return AgentCard(
        name="summarizer_agent",
        description=(
            "Summarizes text using Gemini 2.0 Flash. "
            "Returns a structured summary, word count, key topics, and sentiment."
        ),
        version="1.0.0",
        endpoint=f"{base_url}/summarize",
        capabilities=["text-summarization", "sentiment-analysis", "topic-extraction"],
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "style": {
                    "type": "string",
                    "enum": ["bullet", "paragraph"],
                    "default": "bullet",
                },
            },
            "required": ["text"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "word_count": {"type": "integer"},
                "key_topics": {"type": "array", "items": {"type": "string"}},
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "neutral", "negative"],
                },
            },
        },
    )


@app.post("/summarize", response_model=SummarizeResponse, tags=["Agent"])
async def summarize(req: SummarizeRequest):
    """
    Run the ADK summarizer agent.

    Accepts a block of text and returns a structured summary produced by
    Gemini 2.0 Flash via the Agent Development Kit (ADK).
    """
    logger.info(
        "Summarize request | user=%s session=%s style=%s chars=%d",
        req.user_id,
        req.session_id,
        req.style,
        len(req.text),
    )

    prompt = (
        f"Summarize the following text using the '{req.style}' style.\n\n"
        f"TEXT:\n{req.text}"
    )

    try:
        raw = await run_agent(req.user_id, req.session_id, prompt)
    except Exception as exc:
        logger.exception("ADK runner error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    # Parse JSON response from the model
    try:
        cleaned = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(cleaned)
        return SummarizeResponse(
            summary=parsed.get("summary", raw),
            word_count=int(parsed.get("word_count", len(req.text.split()))),
            key_topics=parsed.get("key_topics", []),
            sentiment=parsed.get("sentiment", "neutral"),
            style=req.style,
        )
    except (json.JSONDecodeError, ValueError):
        logger.warning("Model did not return valid JSON; using raw fallback.")
        return SummarizeResponse(
            summary=raw,
            word_count=len(req.text.split()),
            key_topics=[],
            sentiment="neutral",
            style=req.style,
        )


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def _global_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Local dev entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
