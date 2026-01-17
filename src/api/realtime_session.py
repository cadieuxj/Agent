"""Real-time session manager for Azure OpenAI Realtime API."""
import asyncio
import json
import logging
from typing import Optional, Dict, Callable
from enum import Enum
import websockets
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session status enumeration."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class RealtimeEvent(BaseModel):
    """Real-time API event."""

    type: str
    event_id: Optional[str] = None
    data: Optional[Dict] = None


class RealtimeSession:
    """Manages a real-time voice session with Azure OpenAI.

    This class handles:
    1. WebSocket connection to Azure OpenAI Realtime API
    2. Session configuration
    3. Audio streaming
    4. Event handling (including barge-in)
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        system_prompt: str,
        voice: str = "alloy",
    ):
        """Initialize realtime session.

        Args:
            endpoint: Azure OpenAI endpoint
            api_key: API key
            deployment: Deployment name (e.g., gpt-4o-realtime)
            system_prompt: System prompt for the agent
            voice: Voice model (alloy, echo, shimmer)
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.system_prompt = system_prompt
        self.voice = voice

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.status = SessionStatus.DISCONNECTED
        self.event_handlers: Dict[str, Callable] = {}

        # Session configuration
        self.turn_detection = {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
        }

    async def connect(self):
        """Connect to Azure OpenAI Realtime API."""
        # Build WebSocket URL
        ws_url = f"{self.endpoint}/openai/realtime"
        ws_url += f"?deployment={self.deployment}"
        ws_url += "&api-version=2024-10-01-preview"

        # Connect
        headers = {
            "api-key": self.api_key,
            "OpenAI-Beta": "realtime=v1",
        }

        try:
            self.status = SessionStatus.CONNECTING
            self.websocket = await websockets.connect(ws_url, extra_headers=headers)
            self.status = SessionStatus.CONNECTED
            logger.info("Connected to Azure OpenAI Realtime API")

            # Configure session
            await self._configure_session()

            # Start event loop
            asyncio.create_task(self._event_loop())

        except Exception as e:
            self.status = SessionStatus.ERROR
            logger.error(f"Failed to connect: {e}")
            raise

    async def _configure_session(self):
        """Configure the session with system prompt and settings."""
        config_event = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.system_prompt,
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": self.turn_detection,
                "temperature": 0.7,
                "max_response_output_tokens": 4096,
            },
        }

        await self._send_event(config_event)
        logger.info("Session configured")

    async def _send_event(self, event: Dict):
        """Send event to the API.

        Args:
            event: Event dictionary
        """
        if self.websocket and self.status == SessionStatus.CONNECTED:
            await self.websocket.send(json.dumps(event))
        else:
            logger.warning("Cannot send event: WebSocket not connected")

    async def _event_loop(self):
        """Main event loop to receive and handle events."""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                try:
                    event = json.loads(message)
                    await self._handle_event(event)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode event: {message}")
                except Exception as e:
                    logger.error(f"Error handling event: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.status = SessionStatus.DISCONNECTED
        except Exception as e:
            logger.error(f"Event loop error: {e}")
            self.status = SessionStatus.ERROR

    async def _handle_event(self, event: Dict):
        """Handle incoming event from API.

        Args:
            event: Event dictionary
        """
        event_type = event.get("type")

        # Call registered handler
        if event_type in self.event_handlers:
            await self.event_handlers[event_type](event)

        # Default handling
        if event_type == "error":
            logger.error(f"API error: {event}")
        elif event_type == "session.created":
            logger.info("Session created")
        elif event_type == "session.updated":
            logger.info("Session updated")
        elif event_type == "response.done":
            logger.debug("Response completed")

    def on_event(self, event_type: str, handler: Callable):
        """Register event handler.

        Args:
            event_type: Event type to handle
            handler: Async function to call when event occurs
        """
        self.event_handlers[event_type] = handler

    async def send_audio(self, audio_data: bytes):
        """Send audio data to the API.

        Args:
            audio_data: PCM16 audio data
        """
        event = {
            "type": "input_audio_buffer.append",
            "audio": audio_data.hex(),  # Send as hex string
        }
        await self._send_event(event)

    async def commit_audio(self):
        """Commit the audio buffer to trigger processing."""
        event = {"type": "input_audio_buffer.commit"}
        await self._send_event(event)

    async def cancel_response(self):
        """Cancel ongoing response (for barge-in).

        This is called when the user starts speaking while the agent is responding.
        """
        event = {"type": "response.cancel"}
        await self._send_event(event)
        logger.info("Response cancelled (barge-in)")

    async def clear_audio_buffer(self):
        """Clear the input audio buffer."""
        event = {"type": "input_audio_buffer.clear"}
        await self._send_event(event)

    async def send_text(self, text: str):
        """Send text message to the conversation.

        Args:
            text: Text message
        """
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        }
        await self._send_event(event)

        # Trigger response
        await self._send_event({"type": "response.create"})

    async def disconnect(self):
        """Disconnect from the API."""
        if self.websocket:
            await self.websocket.close()
            self.status = SessionStatus.DISCONNECTED
            logger.info("Disconnected from API")


class SessionManager:
    """Manages multiple realtime sessions."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, RealtimeSession] = {}

    async def create_session(
        self,
        session_id: str,
        endpoint: str,
        api_key: str,
        deployment: str,
        system_prompt: str,
        voice: str = "alloy",
    ) -> RealtimeSession:
        """Create a new session.

        Args:
            session_id: Unique session identifier
            endpoint: Azure OpenAI endpoint
            api_key: API key
            deployment: Deployment name
            system_prompt: System prompt
            voice: Voice model

        Returns:
            RealtimeSession instance
        """
        session = RealtimeSession(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            system_prompt=system_prompt,
            voice=voice,
        )

        await session.connect()
        self.sessions[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[RealtimeSession]:
        """Get existing session.

        Args:
            session_id: Session identifier

        Returns:
            RealtimeSession or None
        """
        return self.sessions.get(session_id)

    async def close_session(self, session_id: str):
        """Close and remove session.

        Args:
            session_id: Session identifier
        """
        session = self.sessions.get(session_id)
        if session:
            await session.disconnect()
            del self.sessions[session_id]

    async def close_all(self):
        """Close all sessions."""
        for session_id in list(self.sessions.keys()):
            await self.close_session(session_id)
