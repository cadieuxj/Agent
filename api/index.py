"""Vercel serverless function entry point for Quebec Voice Agent API."""
import logging
import uuid
import sys
import os
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from mangum import Mangum

from src.config.settings import settings
from src.agents.router_agent import RouterAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Quebec Voice Agent API",
    description="Production-ready voice agent for commercial vehicle sales in Quebec",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize router agent (stateless, safe for serverless)
router_agent = RouterAgent(default_language=settings.default_language)


class SessionRequest(BaseModel):
    """Session creation request."""
    language: Optional[str] = None
    geolocation: Optional[str] = None
    agent_type: Optional[str] = "sales"


class LanguageDetectionRequest(BaseModel):
    """Language detection request."""
    text: str
    geolocation: Optional[str] = None


class RouteRequest(BaseModel):
    """Route request."""
    text: str


@app.get("/")
@app.get("/api")
async def root():
    """Health check endpoint."""
    return {
        "service": "Quebec Voice Agent",
        "status": "healthy",
        "version": "1.0.0",
        "platform": "vercel",
    }


@app.get("/api/health")
@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "default_language": settings.default_language,
        "quebec_compliance": settings.quebec_compliance_mode,
        "platform": "vercel-serverless",
        "note": "WebSocket sessions require separate persistent connection service",
    }


@app.post("/api/session/create")
@app.post("/session/create")
async def create_session(request: SessionRequest):
    """Create session configuration (stateless - returns config for client).

    Note: In Vercel serverless, we cannot maintain WebSocket connections.
    This endpoint returns configuration for the client to connect directly
    to Azure OpenAI Realtime API or a separate WebSocket service.

    Args:
        request: Session creation request

    Returns:
        Session configuration for client-side connection
    """
    # Detect language
    language = request.language or settings.default_language
    if request.geolocation:
        if request.geolocation.upper() in ["QUEBEC", "QC", "QUÉBEC"]:
            language = "fr-CA"

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Get system prompt for the agent type
    system_prompt = router_agent.get_system_prompt(language, request.agent_type)

    return {
        "session_id": session_id,
        "status": "configured",
        "language": language,
        "agent_type": request.agent_type,
        "system_prompt": system_prompt,
        "azure_config": {
            "endpoint": settings.azure_openai_endpoint,
            "deployment": settings.azure_openai_deployment_name,
            "api_version": settings.azure_openai_api_version,
        },
        "note": "Use client-side SDK to connect to Azure OpenAI Realtime API directly",
    }


@app.post("/api/detect-language")
@app.post("/test/detect-language")
async def detect_language(request: LanguageDetectionRequest):
    """Detect language from text.

    Args:
        request: Language detection request

    Returns:
        Language detection result
    """
    result = router_agent.detect_language(request.text, request.geolocation)
    return result.dict()


@app.post("/api/route-request")
@app.post("/test/route-request")
async def route_request(request: RouteRequest):
    """Route a request to the appropriate agent.

    Args:
        request: Route request

    Returns:
        Routing decision
    """
    return router_agent.route_request(request.text)


@app.get("/api/config")
async def get_config():
    """Get client configuration for Azure OpenAI Realtime API connection.

    Returns configuration needed for browser-based WebRTC/WebSocket
    connections directly to Azure OpenAI.
    """
    return {
        "azure_openai": {
            "endpoint": settings.azure_openai_endpoint,
            "deployment": settings.azure_openai_deployment_name,
            "api_version": settings.azure_openai_api_version,
        },
        "default_language": settings.default_language,
        "quebec_compliance": settings.quebec_compliance_mode,
        "supported_agents": ["sales", "finance", "engineering"],
    }


# Catch-all for undefined routes
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path: str):
    """Handle undefined routes."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": f"/{path}",
            "available_endpoints": [
                "GET /",
                "GET /api/health",
                "POST /api/session/create",
                "POST /api/detect-language",
                "POST /api/route-request",
                "GET /api/config",
            ],
        },
    )


# Vercel serverless handler using Mangum
handler = Mangum(app, lifespan="off")
