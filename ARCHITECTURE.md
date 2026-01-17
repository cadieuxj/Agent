# Quebec Voice Agent - Architecture Documentation

## System Architecture

### Overview

The Quebec Voice Agent is a production-ready, low-latency voice assistant built on a multi-agent architecture with specialized agents for different domains in commercial vehicle sales.

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Web Client (HTML5 + JavaScript)                           │  │
│  │ - WebSocket connection                                    │  │
│  │ - Web Audio API for capture/playback                      │  │
│  │ - Voice Activity Detection (VAD)                          │  │
│  │ - Barge-in detection (-45 dBFS threshold)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ WebSocket (PCM16 Audio)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ FastAPI Application                                       │  │
│  │ - Session management                                      │  │
│  │ - WebSocket handling                                      │  │
│  │ - CORS & authentication                                   │  │
│  │ - Health checks & monitoring                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Real-Time AI Layer                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Azure OpenAI Realtime API                                 │  │
│  │ - GPT-4o Realtime Model                                   │  │
│  │ - Streaming audio I/O                                     │  │
│  │ - Server-side VAD                                         │  │
│  │ - Multi-modal (text + audio)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestration Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Router Agent                                              │  │
│  │ - Language detection (FR-CA vs EN-US)                     │  │
│  │ - Intent classification                                   │  │
│  │ - Agent selection                                         │  │
│  └─────────────┬───────────────┬─────────────┬───────────────┘  │
│                │               │             │                   │
│    ┌───────────▼───┐  ┌────────▼──────┐  ┌──▼──────────────┐  │
│    │ Sales Agent   │  │ Finance Agent │  │ Engineering Agent│  │
│    │               │  │               │  │                  │  │
│    │ Text-to-SQL   │  │ TRAC Calc     │  │ RAG Search       │  │
│    │ VIN Decoder   │  │ Bill 96       │  │ GVWR Calc        │  │
│    └───────────────┘  └───────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   SQLite/    │  │Azure AI      │  │ Azure Document       │ │
│  │  PostgreSQL  │  │Search        │  │ Intelligence         │ │
│  │              │  │              │  │                      │ │
│  │ Vehicle      │  │ Vector       │  │ PDF Processing       │ │
│  │ Inventory    │  │ Embeddings   │  │ (Body Builders)      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Router Agent

**Purpose**: Intelligent request routing and language detection

**Responsibilities**:
- Detect language (FR-CA vs EN-US) using pattern matching
- Default to fr-CA for Quebec geolocations
- Classify user intent (sales, finance, engineering)
- Select appropriate specialized agent
- Generate agent-specific system prompts

**Key Features**:
- Pattern-based language detection
- Quebec French terminology recognition
- Bill 96 compliance awareness
- Seamless agent handoff

### 2. Sales Agent

**Purpose**: Vehicle inventory search and VIN decoding

**Capabilities**:
- Natural language to SQL query translation
- Vehicle inventory search (Make, Model, Year, Price, GVWR)
- VIN decoding via NHTSA vPIC API
- Retrieve brake system type and fuel type

**Tools**:
- `VinDecoderTool`: NHTSA API integration
- `InventoryQuery`: Structured query builder
- SQLAlchemy ORM for database access

**Example Queries**:
- "Je cherche un Ford F-150 de 2020"
- "Show me diesel trucks under $50,000"
- "Camions classe 4 disponibles"

### 3. Finance Manager Agent

**Purpose**: Lease calculations and financial disclosures

**Capabilities**:
- TRAC lease payment calculation
- Traditional financing options
- Bill 96 compliant disclosures
- Residual value risk explanation

**TRAC Formula**:
```
P_rent = (C_adj + R) × MF

Where:
- P_rent = Monthly rental payment
- C_adj = Adjusted capitalized cost (price - down payment)
- R = Residual value
- MF = Money factor (APR / 2400)
```

**Compliance**:
- French-first financial disclosures (Bill 96)
- Mandatory TRAC risk warnings
- Clear explanation of open-ended lease terms

### 4. Engineering Expert Agent

**Purpose**: Technical assistance for upfits and modifications

**Capabilities**:
- RAG-powered document search (Body Builder guides)
- PTO (Power Take-Off) specifications
- GVWR compliance calculations
- Upfit weight recommendations

**Tools**:
- RAG Pipeline with vector search
- Document Intelligence for PDF parsing
- GVWR calculator

**Knowledge Base**:
- Engine-driven PTO specs
- Transmission PTO specs
- Split-shaft PTO specs
- Upfit weight tables
- Safety clearance requirements

## Real-Time Voice Pipeline

### Audio Flow

```
Client Microphone
      │
      │ (Float32 PCM, 16kHz)
      ▼
Web Audio API
      │
      │ Convert to Int16
      ▼
WebSocket Send
      │
      │ (Hex-encoded PCM16)
      ▼
FastAPI Server
      │
      │ Decode hex
      ▼
Azure OpenAI Realtime API
      │
      │ Process & generate response
      ▼
Audio Response
      │
      │ (Hex-encoded PCM16)
      ▼
WebSocket Receive
      │
      │ Decode & convert
      ▼
Web Audio API Playback
      │
      ▼
Client Speakers
```

### Barge-In Logic

**Client-Side VAD**:
1. Monitor audio level using AnalyserNode
2. Calculate RMS and convert to dBFS
3. If level > -45 dBFS AND agent is speaking:
   - Suspend audio context
   - Send `barge_in` event to server
   - Clear audio buffer
4. Server cancels ongoing response
5. Resume audio context after 500ms

**Benefits**:
- Natural conversation flow
- Immediate response to user input
- No waiting for agent to finish

## Data Integration

### Vehicle Inventory

**Schema**:
```sql
CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY,
    vin VARCHAR(17) UNIQUE,
    make VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    price FLOAT,
    gvwr_class VARCHAR(50),
    brake_system_type VARCHAR(100),
    primary_fuel_type VARCHAR(50),
    body_class VARCHAR(100),
    ...
);
```

**Ingestion**:
```bash
python src/data/ingest_vehicles.py --csv data/inventory/vehicles.csv
```

### VIN Decoding

**NHTSA vPIC API**:
- Endpoint: `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}`
- Returns: Make, Model, Year, Brake System, Fuel Type, GVWR, etc.
- Caching: Results cached for performance

### RAG Pipeline

**Document Processing**:
1. PDF ingestion using Azure Document Intelligence
2. Layout model extracts tables and text
3. Convert tables to Markdown format
4. Chunk documents (page-level)
5. Generate embeddings (Azure OpenAI)
6. Store in vector database (Azure AI Search)

**Search**:
1. User query → embedding
2. Cosine similarity search
3. Retrieve top-k relevant chunks
4. Pass to agent as context
5. Agent synthesizes answer

## Deployment Architecture

### Azure Container Apps

```
┌─────────────────────────────────────────────────────────────┐
│                   Azure Container Apps                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Container Instances (2-20 replicas)                   │   │
│  │ - quebec-voice-agent:latest                           │   │
│  │ - Health checks: /health                              │   │
│  │ - Resource limits: 2 CPU, 4Gi memory                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ KEDA Auto-Scaler                                      │   │
│  │ - Active connections > 50 → scale up                  │   │
│  │ - CPU > 70% → scale up                                │   │
│  │ - Memory > 80% → scale up                             │   │
│  │ - Min replicas: 2                                     │   │
│  │ - Max replicas: 20                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Managed Identity                                      │   │
│  │ - Azure OpenAI access                                 │   │
│  │ - Azure AI Search access                              │   │
│  │ - Azure Document Intelligence access                  │   │
│  │ - No API keys in environment                          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Scaling Behavior

**Scale Up Triggers**:
- Active WebSocket connections > 50 per pod
- CPU utilization > 70%
- Memory utilization > 80%
- HTTP request rate > 100 req/s

**Scale Down**:
- Stabilization window: 5 minutes
- Gradual scale down: 50% reduction per minute
- Never scale below min replicas (2)

**Performance Targets**:
- Latency: < 300ms (p95)
- Availability: 99.9%
- Concurrent connections: 1000+

## Security & Compliance

### Bill 96 Compliance

**Requirements**:
1. French-first financial disclosures
2. Contracts in French
3. Quebec French terminology
4. Right to French services

**Implementation**:
- System prompts enforce French-first
- TRAC warnings in French (mandatory)
- Compliance disclaimer in every session
- Quebec terminology database

### Security Measures

**Authentication**:
- Managed Identity for Azure services
- No API keys in code or environment
- Token-based session management

**Data Protection**:
- TLS/SSL for all connections
- No audio recording by default
- Ephemeral session data
- PIPEDA compliance

**Network Security**:
- Network policies (ingress/egress)
- Private VNet integration
- DDoS protection via Azure

## Monitoring & Observability

### Metrics

**Application Metrics**:
- Active sessions count
- Average session duration
- Request latency (p50, p95, p99)
- Error rate
- Agent routing distribution

**Infrastructure Metrics**:
- CPU utilization
- Memory utilization
- Network I/O
- Pod count (current/desired)
- Scaling events

**Business Metrics**:
- Language distribution (FR-CA vs EN-US)
- Agent usage (sales vs finance vs engineering)
- Conversion rate
- Average response time

### Logging

**Log Levels**:
- DEBUG: Development only
- INFO: Normal operations
- WARNING: Potential issues
- ERROR: Failures requiring attention

**Structured Logging**:
```json
{
  "timestamp": "2024-01-17T12:00:00Z",
  "level": "INFO",
  "session_id": "abc123",
  "agent": "sales",
  "language": "fr-CA",
  "message": "Session created"
}
```

## Future Enhancements

### Planned Features

1. **Multi-modal input**: Support for document upload
2. **Voice cloning**: Custom voice per dealership
3. **Analytics dashboard**: Real-time insights
4. **CRM integration**: Salesforce, Dynamics 365
5. **Mobile app**: iOS and Android clients

### Scalability Roadmap

1. **Geographic distribution**: Multi-region deployment
2. **CDN integration**: Static asset optimization
3. **Database sharding**: Horizontal scaling
4. **Caching layer**: Redis for hot data
5. **Queue-based architecture**: Async processing

---

For implementation details, see the source code and README.md.
