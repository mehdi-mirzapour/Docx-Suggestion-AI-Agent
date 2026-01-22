#!/bin/bash
set -e

# --- Configuration ---
RESOURCE_GROUP="docxai-rg"
LOCATION="westeurope"
ACR_NAME="docxaicr"
ENV_NAME="docxai-env"

# Load OpenAI key from .env if available
if [ -f .env ]; then
    export $(grep OPENAI_API_KEY .env | xargs)
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set. Please set it in your .env file or environment."
    exit 1
fi

echo "🚀 Starting DocxAI Automated ACA Deployment..."

# 1. Infrastructure Setup
echo "🏗️ Checking Infrastructure (RG & ACR)..."
if ! az group show --name $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "   -> Creating Resource Group: $RESOURCE_GROUP"
    az group create --name $RESOURCE_GROUP --location $LOCATION
fi

if ! az acr show --name $ACR_NAME >/dev/null 2>&1; then
    echo "   -> Creating Container Registry: $ACR_NAME"
    az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true
else
    echo "   -> Ensuring ACR Admin is enabled"
    az acr update --name $ACR_NAME --admin-enabled true
fi

# 2. ACR Login
echo "🔐 Logging into ACR..."
az acr login --name $ACR_NAME
ACR_URL="$ACR_NAME.azurecr.io"

# 3. Build & Push Images
echo "🔨 Building and Pushing Docker Images..."
docker build --platform linux/amd64 -f Dockerfile.mcp -t $ACR_URL/docxai-mcp:latest .
docker push $ACR_URL/docxai-mcp:latest

docker build --platform linux/amd64 -f Dockerfile.frontend -t $ACR_URL/docxai-frontend:latest .
docker push $ACR_URL/docxai-frontend:latest

docker build --platform linux/amd64 -f Dockerfile.nginx -t $ACR_URL/docxai-nginx:latest .
docker push $ACR_URL/docxai-nginx:latest

# 4. ACA Environment Setup
echo "🌍 Setting up ACA Environment..."
if ! az containerapp env show --name $ENV_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    az containerapp env create --name $ENV_NAME --resource-group $RESOURCE_GROUP --location $LOCATION
fi

# 5. Deploy Containers
echo "🚢 Deploying Container Apps..."

# Deploy MCP (Internal)
echo "   -> Deploying MCP..."
az containerapp create \
  --name mcp \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_URL/docxai-mcp:latest \
  --target-port 8787 \
  --ingress internal \
  --env-vars OPENAI_API_KEY="$OPENAI_API_KEY"

# Deploy Frontend (Internal)
echo "   -> Deploying Frontend..."
az containerapp create \
  --name frontend \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_URL/docxai-frontend:latest \
  --target-port 80 \
  --ingress internal

# Deploy Nginx (External - Gateway)
echo "   -> Deploying Nginx..."
az containerapp create \
  --name nginx-gateway \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_URL/docxai-nginx:latest \
  --target-port 80 \
  --ingress external

echo "✅ ACA Deployment Complete!"
GW_URL=$(az containerapp show --name nginx-gateway --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
echo "📍 App URL: https://$GW_URL"
echo "👉 Note: It may take a minute for the gateway to reach the internal services."
