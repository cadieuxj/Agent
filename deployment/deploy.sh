#!/bin/bash
# Quebec Voice Agent - Azure Container Apps Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="rg-quebec-voice-agent"
LOCATION="canadacentral"
CONTAINER_APP_ENV="voice-agent-env"
CONTAINER_APP_NAME="quebec-voice-agent"
ACR_NAME="quebecvoiceagentacr"

echo -e "${GREEN}Quebec Voice Agent - Azure Deployment${NC}"
echo "========================================"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    exit 1
fi

# Login to Azure
echo -e "${YELLOW}Logging in to Azure...${NC}"
az login

# Create Resource Group
echo -e "${YELLOW}Creating resource group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION

# Create Azure Container Registry
echo -e "${YELLOW}Creating Azure Container Registry...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Standard \
    --admin-enabled true

# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Build and push Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t $ACR_LOGIN_SERVER/quebec-voice-agent:latest -f deployment/Dockerfile .

echo -e "${YELLOW}Pushing image to ACR...${NC}"
docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD
docker push $ACR_LOGIN_SERVER/quebec-voice-agent:latest

# Create Azure OpenAI resource
echo -e "${YELLOW}Creating Azure OpenAI resource...${NC}"
az cognitiveservices account create \
    --name quebec-voice-openai \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --kind OpenAI \
    --sku S0

# Deploy GPT-4o Realtime model
echo -e "${YELLOW}Deploying GPT-4o Realtime model...${NC}"
az cognitiveservices account deployment create \
    --name quebec-voice-openai \
    --resource-group $RESOURCE_GROUP \
    --deployment-name gpt-4o-realtime \
    --model-name gpt-4o-realtime \
    --model-version "2024-10-01" \
    --model-format OpenAI \
    --sku-capacity 1 \
    --sku-name "Standard"

# Get OpenAI endpoint and key
OPENAI_ENDPOINT=$(az cognitiveservices account show \
    --name quebec-voice-openai \
    --resource-group $RESOURCE_GROUP \
    --query properties.endpoint \
    --output tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
    --name quebec-voice-openai \
    --resource-group $RESOURCE_GROUP \
    --query key1 \
    --output tsv)

# Create Azure AI Search
echo -e "${YELLOW}Creating Azure AI Search...${NC}"
az search service create \
    --name quebec-voice-search \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard

SEARCH_ENDPOINT="https://quebec-voice-search.search.windows.net"
SEARCH_KEY=$(az search admin-key show \
    --service-name quebec-voice-search \
    --resource-group $RESOURCE_GROUP \
    --query primaryKey \
    --output tsv)

# Create Azure Document Intelligence
echo -e "${YELLOW}Creating Azure Document Intelligence...${NC}"
az cognitiveservices account create \
    --name quebec-voice-di \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --kind FormRecognizer \
    --sku S0

DI_ENDPOINT=$(az cognitiveservices account show \
    --name quebec-voice-di \
    --resource-group $RESOURCE_GROUP \
    --query properties.endpoint \
    --output tsv)

DI_KEY=$(az cognitiveservices account keys list \
    --name quebec-voice-di \
    --resource-group $RESOURCE_GROUP \
    --query key1 \
    --output tsv)

# Create Container Apps environment
echo -e "${YELLOW}Creating Container Apps environment...${NC}"
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION

# Create secrets
echo -e "${YELLOW}Creating Container App with secrets...${NC}"
az containerapp create \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image $ACR_LOGIN_SERVER/quebec-voice-agent:latest \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 8000 \
    --ingress external \
    --min-replicas 2 \
    --max-replicas 20 \
    --cpu 2.0 \
    --memory 4Gi \
    --secrets \
        azure-openai-endpoint=$OPENAI_ENDPOINT \
        azure-openai-api-key=$OPENAI_KEY \
        azure-search-endpoint=$SEARCH_ENDPOINT \
        azure-search-key=$SEARCH_KEY \
        azure-di-endpoint=$DI_ENDPOINT \
        azure-di-key=$DI_KEY \
    --env-vars \
        AZURE_OPENAI_ENDPOINT=secretref:azure-openai-endpoint \
        AZURE_OPENAI_API_KEY=secretref:azure-openai-api-key \
        AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-realtime \
        AZURE_OPENAI_API_VERSION=2024-10-01-preview \
        AZURE_AI_SEARCH_ENDPOINT=secretref:azure-search-endpoint \
        AZURE_AI_SEARCH_KEY=secretref:azure-search-key \
        AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=secretref:azure-di-endpoint \
        AZURE_DOCUMENT_INTELLIGENCE_KEY=secretref:azure-di-key \
        DEFAULT_LANGUAGE=fr-CA \
        QUEBEC_COMPLIANCE_MODE=true \
        VAD_THRESHOLD_DBFS=-45 \
        MAX_CONNECTIONS=100

# Enable managed identity
echo -e "${YELLOW}Enabling managed identity...${NC}"
az containerapp identity assign \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --system-assigned

# Configure KEDA scaling rules
echo -e "${YELLOW}Configuring auto-scaling rules...${NC}"
az containerapp update \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --scale-rule-name http-rule \
    --scale-rule-type http \
    --scale-rule-http-concurrency 50

az containerapp update \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --scale-rule-name cpu-rule \
    --scale-rule-type cpu \
    --scale-rule-metadata value=70

# Get app URL
APP_URL=$(az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    --output tsv)

echo -e "${GREEN}Deployment complete!${NC}"
echo "========================================"
echo -e "Application URL: ${GREEN}https://$APP_URL${NC}"
echo -e "Health check: ${GREEN}https://$APP_URL/health${NC}"
echo ""
echo "Next steps:"
echo "1. Test the health endpoint"
echo "2. Ingest vehicle data: python src/data/ingest_vehicles.py"
echo "3. Ingest PDF documents for RAG: python src/data/rag_pipeline.py"
echo "4. Access the client at: client/voice-client.html"
echo ""
echo -e "${YELLOW}Monitor logs:${NC}"
echo "az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
