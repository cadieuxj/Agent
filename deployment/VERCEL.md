# Vercel Deployment Guide

## Overview

This application is configured for Vercel serverless deployment. The API runs as Python serverless functions.

## Architecture Notes

**Important**: Vercel serverless functions are stateless and have execution time limits. The original WebSocket-based real-time voice streaming is not compatible with Vercel's serverless model.

### What works on Vercel:
- REST API endpoints (health checks, session configuration, language detection, routing)
- Stateless request/response operations

### What requires separate infrastructure:
- WebSocket connections for real-time audio streaming
- Persistent session management
- Long-running voice conversations

### Recommended Architecture:
1. **Vercel** - API layer for configuration, routing, and stateless operations
2. **Azure OpenAI Realtime API** - Direct client-side connection for voice streaming
3. **Optional**: Separate WebSocket service (Azure Container Apps, Railway, Fly.io) for server-side audio processing

## Deployment Steps

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Configure Environment Variables
In Vercel Dashboard or via CLI, set these secrets:

```bash
vercel secrets add azure_openai_endpoint "https://your-resource.openai.azure.com/"
vercel secrets add azure_openai_api_key "your-api-key"
vercel secrets add azure_openai_deployment_name "gpt-realtime-mini"
vercel secrets add azure_openai_api_version "2024-12-17"
vercel secrets add azure_ai_search_endpoint "https://your-search.search.windows.net"
vercel secrets add azure_ai_search_key "your-search-key"
vercel secrets add database_url "your-cloud-database-url"
```

### 3. Deploy
```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/health` | GET | Detailed health check |
| `/api/session/create` | POST | Create session configuration |
| `/api/detect-language` | POST | Detect language from text |
| `/api/route-request` | POST | Route request to appropriate agent |
| `/api/config` | GET | Get client configuration |

## Client-Side Integration

Since WebSocket streaming is not available in Vercel serverless, clients should:

1. Call `/api/session/create` to get session configuration
2. Use the returned `azure_config` to connect directly to Azure OpenAI Realtime API
3. Use Azure OpenAI's JavaScript SDK for browser-based voice streaming

Example client flow:
```javascript
// 1. Get session config from Vercel API
const response = await fetch('/api/session/create', {
  method: 'POST',
  body: JSON.stringify({ language: 'fr-CA', agent_type: 'sales' })
});
const config = await response.json();

// 2. Connect to Azure OpenAI Realtime API directly
// Use config.azure_config for connection parameters
// Use config.system_prompt for agent behavior
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with Vercel CLI
vercel dev

# Or run FastAPI directly
uvicorn api.index:app --reload
```

## Troubleshooting

### Function timeout errors
- Vercel has a 60-second max duration for serverless functions
- Ensure operations complete within this limit

### Import errors
- Check that `src/` modules are accessible from `api/index.py`
- The path is added via `sys.path.insert()` in the entry point

### Missing environment variables
- Verify secrets are set in Vercel dashboard
- Check variable names match `vercel.json` configuration
