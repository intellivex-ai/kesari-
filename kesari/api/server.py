"""
Kesari AI — Mobile Companion API
A FastAPI server that exposes Kesari over HTTP REST + WebSocket so you can
chat from any device on your local network (phone, tablet, browser).

Endpoints:
  GET  /           → Serve the web client HTML
  POST /chat       → Single-turn REST chat
  WS   /ws/chat    → Streaming WebSocket chat (server-sent tokens)
  GET  /health     → Health check
  GET  /agents     → List available agents
  GET  /profile    → Current user profile
  GET  /stats      → System + memory stats
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── FastAPI App ──────────────────────────────────────────────

app = FastAPI(
    title="Kesari AI Companion API",
    description="Local API bridge to the Kesari AI desktop assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# These are injected by KesariApp.start_api_server()
_orchestrator = None
_ai_client = None
_user_profile = None
_system_monitor = None
_long_term_memory = None


def configure(
    orchestrator,
    ai_client,
    user_profile=None,
    system_monitor=None,
    long_term_memory=None,
):
    """Called by KesariApp to inject live service references."""
    global _orchestrator, _ai_client, _user_profile, _system_monitor, _long_term_memory
    _orchestrator = orchestrator
    _ai_client = ai_client
    _user_profile = user_profile
    _system_monitor = system_monitor
    _long_term_memory = long_term_memory
    logger.info("Kesari API configured with live services")


# ── Request / Response Models ─────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    agent: str | None = None   # Optional override: "research" | "coding" | "system" | "general"


class ChatResponse(BaseModel):
    reply: str
    agent_used: str


# ── Web Client HTML ───────────────────────────────────────────

_WEB_CLIENT = Path(__file__).parent / "web_client.html"


@app.get("/", response_class=HTMLResponse)
async def serve_web_client():
    """Serve the mobile-optimised web client."""
    if _WEB_CLIENT.exists():
        return HTMLResponse(_WEB_CLIENT.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Kesari AI — web client not found</h1>", status_code=404)


# ── Health ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Kesari AI Companion API"}


# ── Agents ───────────────────────────────────────────────────

@app.get("/agents")
async def list_agents():
    from kesari.ai_brain.agent_orchestrator import AgentOrchestrator
    return {"agents": AgentOrchestrator.list_agents()}


# ── User Profile ─────────────────────────────────────────────

@app.get("/profile")
async def get_profile():
    if not _user_profile:
        raise HTTPException(status_code=503, detail="Profile service not configured")
    return _user_profile.profile


# ── Stats ────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats():
    result: dict[str, Any] = {}
    if _system_monitor:
        try:
            result["system"] = _system_monitor.get_snapshot()
        except Exception:
            pass
    return result


# ── REST Chat ────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Single-turn, non-streaming chat. Returns the full response."""
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="AI services not ready")

    # Add the user message to the ai_client's history so context is preserved
    _ai_client.add_user_message(req.message)

    full_reply = ""
    agent_name = "GeneralAgent"

    async for event in _orchestrator.run(
        user_message=req.message,
        override_agent=req.agent,
    ):
        if event["type"] == "token":
            full_reply += event["content"]
        elif event["type"] == "agent_selected":
            agent_name = event["agent"]
        elif event["type"] == "error":
            raise HTTPException(status_code=500, detail=event["content"])

    return ChatResponse(reply=full_reply, agent_used=agent_name)


# ── WebSocket Streaming Chat ──────────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """
    Streaming chat over WebSocket.
    Client sends: {"message": "...", "agent": null}
    Server yields: {"type": "token"|"agent_selected"|"done"|"error", ...}
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            message = data.get("message", "").strip()
            agent_override = data.get("agent")

            if not message:
                continue

            if not _orchestrator:
                await websocket.send_json({"type": "error", "content": "AI services not ready"})
                continue

            _ai_client.add_user_message(message)

            async for event in _orchestrator.run(
                user_message=message,
                override_agent=agent_override,
            ):
                await websocket.send_json(event)

            await websocket.send_json({"type": "done", "content": ""})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
