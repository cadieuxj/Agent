"""FastAPI application for Quebec Voice Agent."""
import logging
import uuid
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config.settings import settings
from src.api.realtime_session import SessionManager
from src.agents.router_agent import RouterAgent
from src.agents.sales_agent import SalesAgent
from src.agents.finance_agent import FinanceAgent
from src.agents.engineering_agent import EngineeringAgent
from src.data.rag_pipeline import RAGPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Quebec Voice Agent API",
    description="Production-ready voice agent for commercial vehicle sales in Quebec",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
session_manager = SessionManager()
router_agent = RouterAgent(default_language=settings.default_language)
sales_agent = SalesAgent(database_url=settings.database_url)
finance_agent = FinanceAgent()
rag_pipeline = RAGPipeline(use_mock=True)  # Use real Azure DI in production
engineering_agent = EngineeringAgent(rag_pipeline=rag_pipeline)


class SessionRequest(BaseModel):
    """Session creation request."""

    language: Optional[str] = None
    geolocation: Optional[str] = None
    agent_type: Optional[str] = "sales"  # sales, finance, engineering


class SDPOffer(BaseModel):
    """WebRTC SDP offer."""

    sdp: str
    type: str = "offer"


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Quebec Voice Agent API")

    # Initialize RAG pipeline
    try:
        # In production, ingest real Body Builder PDFs
        logger.info("Initializing RAG pipeline")
        # await rag_pipeline.ingest_documents(["./data/pdfs/body_builder_guide.pdf"])
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Quebec Voice Agent API")
    await session_manager.close_all()
    await sales_agent.close()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Quebec Voice Agent",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "max_connections": settings.max_connections,
        "default_language": settings.default_language,
        "quebec_compliance": settings.quebec_compliance_mode,
    }


@app.post("/session/create")
async def create_session(request: SessionRequest):
    """Create a new voice session.

    Args:
        request: Session creation request

    Returns:
        Session information
    """
    # Check connection limit
    if len(session_manager.sessions) >= settings.max_connections:
        raise HTTPException(status_code=503, detail="Maximum connections reached")

    # Detect language
    language = request.language or settings.default_language
    if request.geolocation:
        # Force fr-CA for Quebec
        if request.geolocation.upper() in ["QUEBEC", "QC", "QUÉBEC"]:
            language = "fr-CA"

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Get system prompt
    system_prompt = router_agent.get_system_prompt(language, request.agent_type)

    # Create session
    try:
        session = await session_manager.create_session(
            session_id=session_id,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment_name,
            system_prompt=system_prompt,
            voice="alloy",
        )

        return {
            "session_id": session_id,
            "status": session.status,
            "language": language,
            "agent_type": request.agent_type,
            "websocket_url": f"/ws/session/{session_id}",
        }

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio streaming.

    This endpoint:
    1. Accepts WebSocket connections from clients
    2. Forwards audio to Azure OpenAI Realtime API
    3. Streams responses back to client
    4. Handles barge-in events

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session {session_id}")

    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    # Set up event handlers to forward to client
    async def forward_audio(event):
        """Forward audio delta to client."""
        if event.get("type") == "response.audio.delta":
            await websocket.send_json({
                "type": "audio",
                "data": event.get("delta"),
            })

    async def forward_transcript(event):
        """Forward transcript to client."""
        if event.get("type") == "response.audio_transcript.delta":
            await websocket.send_json({
                "type": "transcript",
                "data": event.get("delta"),
            })

    session.on_event("response.audio.delta", forward_audio)
    session.on_event("response.audio_transcript.delta", forward_transcript)

    try:
        while True:
            # Receive from client
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "audio":
                # Client sending audio data
                audio_data = bytes.fromhex(message.get("data"))
                await session.send_audio(audio_data)

            elif msg_type == "audio_end":
                # Client finished speaking
                await session.commit_audio()

            elif msg_type == "barge_in":
                # Client detected barge-in (user started speaking during response)
                logger.info(f"Barge-in detected for session {session_id}")
                await session.cancel_response()
                await session.clear_audio_buffer()

            elif msg_type == "text":
                # Text message
                text = message.get("data")
                await session.send_text(text)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        await session_manager.close_session(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await session_manager.close_session(session_id)


@app.post("/webrtc/offer")
async def webrtc_offer(offer: SDPOffer, session_id: Optional[str] = None):
    """Handle WebRTC SDP offer and return answer.

    This endpoint handles the WebRTC handshake between the browser and
    the Azure OpenAI Realtime API.

    Args:
        offer: SDP offer from client
        session_id: Optional existing session ID

    Returns:
        SDP answer
    """
    # Note: This is a simplified implementation
    # In production, you would:
    # 1. Parse the SDP offer
    # 2. Create ICE candidates
    # 3. Establish peer connection with Azure OpenAI
    # 4. Return SDP answer

    # For now, we recommend using WebSocket approach which is simpler
    raise HTTPException(
        status_code=501,
        detail="WebRTC direct connection not implemented. Use WebSocket endpoint instead.",
    )


@app.get("/sessions/active")
async def get_active_sessions():
    """Get list of active sessions."""
    return {
        "count": len(session_manager.sessions),
        "sessions": list(session_manager.sessions.keys()),
    }


@app.delete("/session/{session_id}")
async def close_session(session_id: str):
    """Close a session.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_manager.close_session(session_id)

    return {
        "status": "closed",
        "session_id": session_id,
    }


# Development/testing endpoints

@app.post("/test/detect-language")
async def test_language_detection(text: str, geolocation: Optional[str] = None):
    """Test language detection.

    Args:
        text: Text to analyze
        geolocation: Optional geolocation

    Returns:
        Language detection result
    """
    result = router_agent.detect_language(text, geolocation)
    return result.dict()


@app.post("/test/route-request")
async def test_routing(text: str):
    """Test request routing.

    Args:
        text: Request text

    Returns:
        Routing decision
    """
    return router_agent.route_request(text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
