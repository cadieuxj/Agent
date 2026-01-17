# Quebec Voice Agent 🇨🇦

Production-ready, low-latency voice agent for commercial vehicle sales in Quebec using the Azure OpenAI GPT-4o Realtime API and Microsoft Agent Framework.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Technical Stack](#technical-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Deployment](#deployment)
- [Compliance](#compliance)
- [API Reference](#api-reference)
- [Development](#development)
- [License](#license)

## Overview

The Quebec Voice Agent is an AI-powered voice assistant specialized in commercial vehicle sales for the Quebec market. It features:

- **Real-time voice interaction** using Azure OpenAI GPT-4o Realtime API
- **Multi-agent architecture** with specialized agents for sales, finance, and engineering
- **Quebec French compliance** with Bill 96 (Charter of the French Language)
- **Intelligent routing** with automatic language detection (FR-CA vs EN-US)
- **Barge-in support** using Voice Activity Detection (VAD)
- **Production-ready deployment** on Azure Container Apps with KEDA auto-scaling

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│  ┌──────────────┐                                          │
│  │ WebRTC/WS    │ ◄──► Voice Activity Detection (VAD)     │
│  │ Client       │      Barge-in: -45 dBFS threshold       │
│  └──────────────┘                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             │ WebSocket / Audio Stream (PCM16)
             ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Middleware                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Session Manager │ WebSocket Handler │ Auth & CORS   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│               Azure OpenAI Realtime API                     │
│              (GPT-4o Realtime Model)                        │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Router Agent                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Language Detection (FR-CA vs EN-US)                  │  │
│  │  Intent Classification                                │  │
│  │  Agent Routing                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────┬────────────┬────────────┬────────────────────────────┘
         │            │            │
         ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌─────────────┐
│   Sales     │ │ Finance  │ │Engineering  │
│   Agent     │ │ Manager  │ │   Expert    │
├─────────────┤ ├──────────┤ ├─────────────┤
│Text-to-SQL  │ │TRAC Calc │ │ RAG Search  │
│Inventory DB │ │Financial │ │Body Builder │
│VIN Decoder  │ │Discl.    │ │GVWR Calc    │
└─────────────┘ └──────────┘ └─────────────┘
```

## Features

### 1. Multi-Agent System

- **Router Agent**: Language detection and request routing
- **Sales Agent**: Inventory search with Text-to-SQL, VIN decoding
- **Finance Manager**: TRAC lease calculations with Bill 96 compliance
- **Engineering Expert**: RAG-powered technical assistance for upfits and PTO

### 2. Real-Time Voice

- **Low-latency streaming** with Azure OpenAI Realtime API
- **Barge-in support** with client-side VAD (-45 dBFS threshold)
- **WebSocket-based** audio streaming (PCM16 format)
- **Session management** with connection pooling

### 3. Quebec Compliance

- **Bill 96 (Charter of the French Language)** compliance
- **French-first financial disclosures**
- **Quebec French terminology** (soumission, camion, fourgon, etc.)
- **Jean-Guy persona** with authentic Quebec voice

### 4. Data Integration

- **SQLite/PostgreSQL** for vehicle inventory
- **NHTSA vPIC API** for VIN decoding (Brake System Type, Fuel Type)
- **Azure AI Search** for vector search
- **Azure Document Intelligence** for PDF parsing (Body Builder guides)

### 5. Production Features

- **KEDA auto-scaling** targeting >50 active connections
- **Managed Identity** for Azure service authentication
- **Health checks** and monitoring
- **Docker containerization**
- **Azure Container Apps** deployment

## Technical Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **AI Orchestration** | Microsoft Agent Framework, Semantic Kernel, AutoGen |
| **Real-Time** | WebRTC (Client), WebSockets (Middleware), Azure OpenAI Realtime API |
| **Database** | SQLite (dev), PostgreSQL (prod), Azure AI Search (vector) |
| **Data Processing** | Azure AI Document Intelligence, Pandas, NumPy |
| **Deployment** | Azure Container Apps, Docker, KEDA |
| **Client** | Vanilla JavaScript, Web Audio API, WebSocket API |

## Project Structure

```
quebec-voice-agent/
├── src/
│   ├── agents/
│   │   ├── router_agent.py          # Language detection & routing
│   │   ├── sales_agent.py           # Inventory search (Text-to-SQL)
│   │   ├── finance_agent.py         # TRAC lease calculator
│   │   └── engineering_agent.py     # RAG-powered technical expert
│   ├── api/
│   │   ├── main.py                  # FastAPI application
│   │   └── realtime_session.py      # Azure OpenAI session manager
│   ├── config/
│   │   ├── settings.py              # Environment configuration
│   │   └── personas.py              # Jean-Guy system prompts
│   ├── data/
│   │   ├── ingest_vehicles.py       # CSV to SQLite ingestion
│   │   └── rag_pipeline.py          # Document processing & RAG
│   ├── models/
│   │   └── vehicle.py               # SQLAlchemy models
│   └── tools/
│       ├── vin_decoder.py           # NHTSA vPIC integration
│       └── trac_calculator.py       # TRAC lease formula
├── client/
│   ├── voice-client.html            # Web client UI
│   └── voice-client.js              # WebSocket & VAD logic
├── deployment/
│   ├── Dockerfile                   # Production Docker image
│   ├── container-apps.yaml          # Azure deployment manifest
│   └── deploy.sh                    # Automated deployment script
├── data/
│   ├── inventory/                   # Vehicle database
│   ├── pdfs/                        # Body Builder guides
│   └── vector_store/                # RAG embeddings
├── requirements.txt
├── .env.example
└── README.md
```

## Setup & Installation

### Prerequisites

- Python 3.11+
- Docker (for containerization)
- Azure subscription with the following services:
  - Azure OpenAI (GPT-4o Realtime access)
  - Azure AI Search
  - Azure Document Intelligence
  - Azure Container Apps
  - Azure Container Registry

### Local Development Setup

1. **Clone the repository**

```bash
git clone https://github.com/your-org/quebec-voice-agent.git
cd quebec-voice-agent
```

2. **Create virtual environment**

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

Required environment variables:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-realtime
AZURE_AI_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_AI_SEARCH_KEY=your-search-key
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-di.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-di-key
```

5. **Initialize database**

```bash
# Create database tables
python src/data/ingest_vehicles.py --recreate-db

# Ingest sample data (if you have a CSV file)
python src/data/ingest_vehicles.py --csv ./data/inventory/Large_Car_Dataset.csv
```

6. **Initialize RAG pipeline** (optional)

```bash
# Process Body Builder PDFs
python src/data/rag_pipeline.py
```

7. **Run the application**

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Open the client**

Open `client/voice-client.html` in a web browser or serve it:

```bash
cd client
python -m http.server 3000
# Navigate to http://localhost:3000/voice-client.html
```

## Usage

### Starting a Voice Session

1. **Open the web client** at `http://localhost:3000/voice-client.html`

2. **Select language** (Français or English)

3. **Choose agent type**:
   - Sales Agent: Vehicle inventory queries
   - Finance Manager: Lease calculations
   - Engineering Expert: Technical questions

4. **Click "Connect"** to establish WebSocket connection

5. **Hold "Hold to Talk"** button to speak

6. The agent will respond with:
   - Real-time voice output
   - Text transcription
   - Automatic barge-in when you interrupt

### Example Conversations

**Sales (French)**

```
User: "Bonjour, je cherche un camion pour la construction."
Jean-Guy: "Bonjour! Parfait pour la construction. Vous avez besoin
           de quelle classe de PNBV? Quelle utilisation exactement?"
```

**Finance (French)**

```
User: "Combien coûte la location TRAC pour un camion à 50 000$?"
Jean-Guy: "Je peux vous calculer ça. Avez-vous une mise de fonds?
           Sur combien de mois? Et IMPORTANT: la location TRAC
           est à durée indéterminée - vous assumez le risque..."
```

**Engineering (French)**

```
User: "Quelles sont les spécifications PTO pour une benne?"
Jean-Guy: "Pour une benne basculante, on utilise généralement un
           PTO de transmission. Couple maximal de 300 lb-ft..."
```

### API Endpoints

**Create Session**

```bash
POST /session/create
Content-Type: application/json

{
  "language": "fr-CA",
  "geolocation": "Quebec",
  "agent_type": "sales"
}
```

**WebSocket Connection**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session/{session_id}');

// Send audio
ws.send(JSON.stringify({
  type: 'audio',
  data: hexEncodedPCM16
}));

// Signal end of speech
ws.send(JSON.stringify({ type: 'audio_end' }));

// Barge-in (interrupt agent)
ws.send(JSON.stringify({ type: 'barge_in' }));
```

**Health Check**

```bash
GET /health

Response:
{
  "status": "healthy",
  "active_sessions": 5,
  "max_connections": 100,
  "default_language": "fr-CA"
}
```

## Deployment

### Azure Container Apps Deployment

**Automated Deployment**

```bash
# Run the deployment script
cd deployment
./deploy.sh
```

This script will:
1. Create Azure resource group
2. Create Azure Container Registry (ACR)
3. Build and push Docker image
4. Create Azure OpenAI resource and deploy GPT-4o Realtime
5. Create Azure AI Search
6. Create Azure Document Intelligence
7. Deploy Container App with KEDA scaling
8. Configure managed identity

**Manual Deployment**

```bash
# Build Docker image
docker build -t quebec-voice-agent:latest -f deployment/Dockerfile .

# Tag for ACR
docker tag quebec-voice-agent:latest yourregistry.azurecr.io/quebec-voice-agent:latest

# Push to ACR
docker push yourregistry.azurecr.io/quebec-voice-agent:latest

# Deploy using Azure CLI
az containerapp create \
  --name quebec-voice-agent \
  --resource-group rg-quebec-voice-agent \
  --environment voice-agent-env \
  --image yourregistry.azurecr.io/quebec-voice-agent:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 20
```

### KEDA Auto-Scaling

The deployment includes KEDA scaling rules:

- **Active Connections**: Scale when >50 connections per pod
- **CPU Utilization**: Scale when CPU >70%
- **Memory Utilization**: Scale when memory >80%
- **Min replicas**: 2
- **Max replicas**: 20

### Monitoring

```bash
# View logs
az containerapp logs show \
  --name quebec-voice-agent \
  --resource-group rg-quebec-voice-agent \
  --follow

# View metrics
az monitor metrics list \
  --resource /subscriptions/{sub-id}/resourceGroups/rg-quebec-voice-agent/providers/Microsoft.App/containerApps/quebec-voice-agent
```

## Compliance

### Bill 96 (Charter of the French Language)

This application complies with Quebec's Bill 96:

1. **French-first financial disclosures**: All financial information is provided in French first
2. **French contracts**: Final contracts are always in French
3. **Quebec French terminology**: Uses Quebec-specific terms (soumission, camion, etc.)
4. **Bilingual support**: Can respond in English, but legal documents remain in French
5. **Compliance disclaimer**: Every session includes Bill 96 compliance notice

### TRAC Lease Compliance

For TRAC (Terminal Rental Adjustment Clause) leases:

1. **Mandatory risk disclosure**: Users are informed that TRAC leases are "open-ended"
2. **Residual value risk**: Clear explanation that lessee bears residual value risk
3. **Financial impact**: Examples of potential costs at end of lease
4. **French disclosure**: All TRAC warnings provided in French first (Bill 96)

### Data Privacy

- No personal data is stored without consent
- Audio streams are not recorded by default
- Session data is ephemeral
- Complies with Canadian privacy laws (PIPEDA)

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint |
| `/health` | GET | Health check |
| `/session/create` | POST | Create new voice session |
| `/session/{id}` | DELETE | Close session |
| `/sessions/active` | GET | List active sessions |
| `/test/detect-language` | POST | Test language detection |
| `/test/route-request` | POST | Test request routing |

### WebSocket Events

**Client → Server**

| Type | Description | Payload |
|------|-------------|---------|
| `audio` | Audio data chunk | `{ type: "audio", data: "hex..." }` |
| `audio_end` | End of speech | `{ type: "audio_end" }` |
| `barge_in` | User interruption | `{ type: "barge_in" }` |
| `text` | Text message | `{ type: "text", data: "Hello" }` |

**Server → Client**

| Type | Description | Payload |
|------|-------------|---------|
| `audio` | Audio response | `{ type: "audio", data: "hex..." }` |
| `transcript` | Text transcript | `{ type: "transcript", data: "Bonjour..." }` |
| `audio_end` | Agent finished | `{ type: "audio_end" }` |

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/

# Type checking
mypy src/

# Linting
flake8 src/
```

### Adding New Agents

1. Create agent class in `src/agents/`
2. Add routing logic in `router_agent.py`
3. Add system prompt in `src/config/personas.py`
4. Register in `src/api/main.py`

### Adding New Tools

1. Create tool class in `src/tools/`
2. Implement async methods
3. Add tool description for agent framework
4. Register with appropriate agent

## License

Copyright © 2024 Quebec Voice Agent Team. All rights reserved.

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Support

For issues, questions, or contributions:

- **GitHub Issues**: https://github.com/your-org/quebec-voice-agent/issues
- **Documentation**: https://docs.quebecvoiceagent.com
- **Email**: support@quebecvoiceagent.com

---

Built with ❤️ in Quebec 🇨🇦
