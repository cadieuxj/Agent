"""Vercel serverless function entry point for Quebec Voice Agent API."""
import logging
import uuid
import sys
import os
from typing import Optional

# Add parent directory to path for src imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app - Vercel looks for 'app' variable
app = FastAPI(
    title="Quebec Voice Agent API",
    description="Production-ready voice agent for commercial vehicle sales in Quebec using GPT-4o Realtime (Mini)",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Lazy loading to avoid import errors during Vercel build
_router_agent = None
_settings = None


def get_settings():
    global _settings
    if _settings is None:
        from src.config.settings import settings
        _settings = settings
    return _settings


def get_router_agent():
    global _router_agent
    if _router_agent is None:
        from src.agents.router_agent import RouterAgent
        settings = get_settings()
        _router_agent = RouterAgent(default_language=settings.default_language)
    return _router_agent


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
    settings = get_settings()
    return {
        "status": "healthy",
        "default_language": settings.default_language,
        "quebec_compliance": settings.quebec_compliance_mode,
        "platform": "vercel-serverless",
    }


@app.post("/api/session/create")
@app.post("/session/create")
async def create_session(request: SessionRequest):
    """Create session configuration for client-side Azure OpenAI connection."""
    try:
        settings = get_settings()

        # Detect language
        language = request.language or settings.default_language
        if request.geolocation:
            if request.geolocation.upper() in ["QUEBEC", "QC", "QUÉBEC"]:
                language = "fr-CA"

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Simple system prompts (avoiding RouterAgent for now to reduce dependencies)
        system_prompts = {
            "sales": f"You are a helpful sales agent for commercial vehicles. Respond in {language}.",
            "finance": f"You are a finance manager specializing in commercial vehicle leasing. Respond in {language}.",
            "engineering": f"You are an engineering expert for commercial vehicles. Respond in {language}.",
        }
        system_prompt = system_prompts.get(request.agent_type, system_prompts["sales"])

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
        }
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.post("/api/detect-language")
@app.post("/test/detect-language")
async def detect_language(request: LanguageDetectionRequest):
    """Detect language from text."""
    router_agent = get_router_agent()
    result = router_agent.detect_language(request.text, request.geolocation)
    return result.dict()


@app.post("/api/route-request")
@app.post("/test/route-request")
async def route_request(request: RouteRequest):
    """Route a request to the appropriate agent."""
    router_agent = get_router_agent()
    return router_agent.route_request(request.text)


@app.get("/api/config")
async def get_config():
    """Get client configuration for Azure OpenAI Realtime API connection."""
    settings = get_settings()
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
