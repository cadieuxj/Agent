# Vercel Migration & GPT-4o Realtime Mini Configuration

## Overview

This document describes the migration from Azure Container Apps to Vercel serverless deployment and the configuration for GPT-4o Realtime Mini (2024-12-17).

## Migration Summary

### From: Azure Container Apps (Docker)
- Full-stack container deployment
- Persistent WebSocket connections
- Stateful session management
- 4 worker processes with auto-scaling (2-20 replicas)

### To: Vercel Serverless
- Stateless serverless functions
- Static frontend hosting
- REST API for session configuration
- Client-side Azure OpenAI connections

## Architecture Changes

### Before (Azure Container Apps)
```
Client → WebSocket → FastAPI → Azure OpenAI Realtime API
         (persistent connection, server-managed audio streaming)
```

### After (Vercel Serverless)
```
Client → REST API → Session Config
  ↓
Client SDK → Azure OpenAI Realtime API (direct connection)
```

## GPT-4o Realtime Mini Configuration

### Model Details
- **Model**: `gpt-4o-realtime-preview-2024-12-17`
- **Deployment Name**: `gpt-realtime-mini`
- **API Version**: `2024-12-17`
- **Features**: Lower latency, cost-effective voice interactions
- **Use Case**: Production voice agents with real-time requirements

### Environment Variables

```bash
# Updated configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/openai/realtime?api-version=2024-12-17&deployment=gpt-realtime-mini
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-realtime-mini
AZURE_OPENAI_API_VERSION=2024-12-17
```

## Files Modified

### Configuration Files
1. **[.env.example](.env.example)** - Updated with Mini model defaults and API version `2024-12-17`
2. **[src/config/settings.py](src/config/settings.py)** - Changed defaults to `gpt-realtime-mini` and `2024-12-17`
3. **[vercel.json](vercel.json)** - Created for Vercel deployment configuration

### API Files
4. **[api/index.py](api/index.py)** - New Vercel serverless entry point (stateless)
5. **[api/requirements.txt](api/requirements.txt)** - Minimal dependencies for serverless
6. **[src/api/main.py](src/api/main.py)** - Updated description to mention Mini model

### Frontend Files
7. **[public/index.html](public/index.html)** - Client interface (copied from `client/`)
8. **[public/voice-client.js](public/voice-client.js)** - Updated for Vercel deployment

### Documentation
9. **[README.md](README.md)** - Updated references to Mini model
10. **[deployment/VERCEL.md](deployment/VERCEL.md)** - Vercel deployment guide
11. **[.vercelignore](.vercelignore)** - Files excluded from deployment

### Archived
12. **deployment/archive/** - Moved Docker/Azure files here

## Deployment Instructions

### 1. Set Environment Variables in Vercel
```bash
vercel env add AZURE_OPENAI_ENDPOINT
vercel env add AZURE_OPENAI_API_KEY
vercel env add AZURE_OPENAI_DEPLOYMENT_NAME
vercel env add AZURE_OPENAI_API_VERSION
```

### 2. Deploy
```bash
vercel --prod
```

### 3. Test Endpoints
- `GET /` - Frontend UI
- `GET /api/health` - Health check
- `POST /api/session/create` - Create session configuration

## Client Integration

The client should:
1. Call `/api/session/create` to get session configuration
2. Use the returned Azure config to connect directly to Azure OpenAI Realtime API
3. Use the returned system prompt for agent behavior

Example:
```javascript
const response = await fetch('/api/session/create', {
  method: 'POST',
  body: JSON.stringify({ language: 'fr-CA', agent_type: 'sales' })
});
const config = await response.json();

// config.azure_config contains:
// - endpoint
// - deployment
// - api_version

// Use these to connect directly to Azure OpenAI Realtime API
```

## Key Differences

| Feature | Azure Container Apps | Vercel Serverless |
|---------|---------------------|-------------------|
| WebSocket Support | ✅ Full support | ⚠️ Limited (requires workaround) |
| Stateful Sessions | ✅ Server-managed | ❌ Client-managed |
| Cold Start | ❌ Always warm | ⚠️ Possible cold starts |
| Scaling | Manual/KEDA | Automatic |
| Cost | Fixed compute | Pay per request |
| Deployment | Docker build + push | Git push |

## Benefits of Mini Model

1. **Lower Latency**: Faster response times for voice interactions
2. **Cost Efficiency**: Reduced token costs compared to full GPT-4o
3. **Production Ready**: Optimized for real-time voice applications
4. **Same API**: Compatible with existing Realtime API code

## Rollback Instructions

To rollback to Azure Container Apps:
1. Move files from `deployment/archive/` back to `deployment/`
2. Update `.env` to use previous API version if needed
3. Deploy using `./deployment/deploy.sh`

## Testing Checklist

- [ ] Health endpoint returns 200
- [ ] Session creation returns valid config
- [ ] Language detection works (FR-CA vs EN-US)
- [ ] Agent routing functions correctly
- [ ] Frontend loads and displays UI
- [ ] API version `2024-12-17` is used in all requests
- [ ] Deployment name `gpt-realtime-mini` is configured

## Notes

- The Realtime Mini model is currently in preview (2024-12-17)
- WebSocket streaming requires separate persistent connection infrastructure
- This deployment is optimized for REST API operations
- For full voice streaming, consider hybrid architecture with separate WebSocket service

## Support

For issues or questions:
- GitHub Issues: [Project Issues](https://github.com/your-org/your-repo/issues)
- Azure OpenAI Docs: [Realtime API Documentation](https://learn.microsoft.com/azure/ai-services/openai/realtime-audio-quickstart)
