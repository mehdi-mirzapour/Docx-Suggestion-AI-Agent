# Azure Container Apps (ACA) Deployment Guide

This guide describes how to deploy the DocxAI solution (MCP, Frontend, and Nginx) using Azure Container Apps. ACA is a serverless platform that simplifies container deployment and scaling.

## Architecture

The deployment consists of three container apps running in a single **Container Apps Environment**:

1.  **mcp-app**: The Python/FastAPI backend and MCP server.
2.  **frontend-app**: The React frontend served via Nginx.
3.  **nginx-app**: The gateway that routes traffic to the frontend and backend.

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- Docker installed and running
- An Azure subscription with a Resource Group

## Quick Start (Automated Script)

The easiest way to deploy is using the provided script:

```bash
chmod +x deploy-aca.sh
./deploy-aca.sh
```

## Manual Deployment Steps

### 1. Create ACR and Push Images
If you haven't already, create an Azure Container Registry and push your images:

```bash
RESOURCE_GROUP="docxai-rg"
ACR_NAME="docxaicr"

# Create ACR
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Login
az acr login --name $ACR_NAME

# Build and Push
ACR_URL="$ACR_NAME.azurecr.io"
docker build -t $ACR_URL/docxai-mcp:latest -f Dockerfile.mcp .
docker build -t $ACR_URL/docxai-frontend:latest -f Dockerfile.frontend .
docker build -t $ACR_URL/docxai-nginx:latest -f Dockerfile.nginx .

docker push $ACR_URL/docxai-mcp:latest
docker push $ACR_URL/docxai-frontend:latest
docker push $ACR_URL/docxai-nginx:latest
```

### 2. Create ACA Environment
The environment acts as a boundary and handles networking for your apps.

```bash
ENV_NAME="docxai-env"
az containerapp env create --name $ENV_NAME --resource-group $RESOURCE_GROUP --location westeurope
```

### 3. Deploy Containers

#### Deploy MCP App (Backend)
```bash
az containerapp create \
  --name docxai-mcp \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_URL/docxai-mcp:latest \
  --target-port 8787 \
  --ingress internal \
  --env-vars OPENAI_API_KEY=your_api_key
```

#### Deploy Frontend App
```bash
az containerapp create \
  --name docxai-frontend \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_URL/docxai-frontend:latest \
  --target-port 80 \
  --ingress internal
```

#### Deploy Nginx App (Gateway)
The Nginx app needs to be configured to route to the internal DNS of the other apps. In ACA, internal DNS is simply the app name.

```bash
az containerapp create \
  --name docxai-nginx \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_URL/docxai-nginx:latest \
  --target-port 80 \
  --ingress external
```

## Critical Notes
- **Ingress:** Only the `nginx-app` should be set to `external`. The `mcp-app` and `frontend-app` should be `internal`.
- **Scaling:** ACA can scale to zero when not in use, saving costs. You can configure this in the Azure Portal or via CLI.
- **Micro-services DNS:** Inside the environment, containers can reach each other via their app name (e.g., `http://docxai-mcp` or `http://docxai-frontend`). ensure your `nginx.conf` supports these names.
