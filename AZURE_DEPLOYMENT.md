# 🚀 Azure Deployment Guide - DocxAI

This document provides a comprehensive guide for deploying the DocxAI application to Azure using **3 Separate App Services** behind **Azure Front Door**.

## 🏗️ Architecture Overview

We deploy 3 distinct containers to 3 distinct App Services for maximum isolation and scalability.

```
       [Azure Front Door] (https://docxai.azurefd.net)
              │
    ┌─────────┼──────────────┐
    ▼         ▼              ▼
[Frontend] [Backend API]   [MCP Server]
(Port 80)    (Port 8787)   (Port 8787)
```

### Routing Rules
- `/*` ➝ **Frontend App Service** (React App)
- `/api/*` ➝ **Backend App Service** (Python REST API)
- `/mcp/*` (or SSE) ➝ **MCP App Service** (ChatGPT Connection)

---

## 1. Prerequisites
Login to Azure:
```bash
az login
az account set --subscription "<your-subscription-id>"
```

## 2. Infrastructure Setup

### A. Create Resource Group & Registry
```bash
# 1. Resource Group
az group create --name docxai-rg --location westeurope

# 2. Container Registry (ACR)
az acr create --resource-group docxai-rg --name docxaiunique123 --sku Basic --admin-enabled true

# Login to ACR locally
az acr login --name docxaiunique123
```

### B. Build & Push Images
You must build and push all 3 images separately.

```bash
export ACR_NAME=docxaiunique123

# 1. Frontend Image
docker build -f Dockerfile.frontend -t $ACR_NAME.azurecr.io/docxai-frontend:latest .
docker push $ACR_NAME.azurecr.io/docxai-frontend:latest

# 2. Backend Image
docker build -f Dockerfile.backend -t $ACR_NAME.azurecr.io/docxai-backend:latest .
docker push $ACR_NAME.azurecr.io/docxai-backend:latest

# 3. MCP Image (Contains critical frontend assets for the panel)
docker build -f Dockerfile.mcp -t $ACR_NAME.azurecr.io/docxai-mcp:latest .
docker push $ACR_NAME.azurecr.io/docxai-mcp:latest
```

## 3. Deploy App Services

We need an App Service Plan and 3 Web Apps.

### A. Create Plan
```bash
az appservice plan create --name docxai-plan --resource-group docxai-rg --sku B1 --is-linux
```

### B. Create 3 Web Apps

**1. Frontend App Service**
```bash
az webapp create --resource-group docxai-rg --plan docxai-plan --name docxai-frontend --deployment-container-image-name $ACR_NAME.azurecr.io/docxai-frontend:latest
```

**2. Backend App Service**
```bash
az webapp create --resource-group docxai-rg --plan docxai-plan --name docxai-backend --deployment-container-image-name $ACR_NAME.azurecr.io/docxai-backend:latest
```

**3. MCP App Service**
```bash
az webapp create --resource-group docxai-rg --plan docxai-plan --name docxai-mcp --deployment-container-image-name $ACR_NAME.azurecr.io/docxai-mcp:latest
```

### C. Configure Settings & Ports

**Link ACR Credentials:**
```bash
export ACR_PASS=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
# Run this for ALL 3 apps:
az webapp config container set --name docxai-frontend --resource-group docxai-rg --docker-registry-server-url https://$ACR_NAME.azurecr.io --docker-registry-server-user $ACR_NAME --docker-registry-server-password $ACR_PASS
az webapp config container set --name docxai-backend --resource-group docxai-rg --docker-registry-server-url https://$ACR_NAME.azurecr.io --docker-registry-server-user $ACR_NAME --docker-registry-server-password $ACR_PASS
az webapp config container set --name docxai-mcp --resource-group docxai-rg --docker-registry-server-url https://$ACR_NAME.azurecr.io --docker-registry-server-user $ACR_NAME --docker-registry-server-password $ACR_PASS
```

**Set Ports & API Key:**
```bash
# Frontend (Nginx listens on 80 by default, so usually no config needed, but safe to set)
az webapp config appsettings set --name docxai-frontend --resource-group docxai-rg --settings WEBSITES_PORT=80

# Backend (Listens on 8787)
az webapp config appsettings set --name docxai-backend --resource-group docxai-rg --settings WEBSITES_PORT=8787 OPENAI_API_KEY="your-key"

# MCP (Listens on 8787)
az webapp config appsettings set --name docxai-mcp --resource-group docxai-rg --settings WEBSITES_PORT=8787 OPENAI_API_KEY="your-key"
```

## 4. Set Up Azure Front Door

1.  **Create Profile**: Create a "Standard" Front Door profile.
2.  **Create Endpoint**: e.g., `docxai-main`.
3.  **Add Origin Groups**:
    *   `frontend-group` -> points to `docxai-frontend.azurewebsites.net`
    *   `backend-group` -> points to `docxai-backend.azurewebsites.net`
    *   `mcp-group` -> points to `docxai-mcp.azurewebsites.net`
4.  **Add Routes**:
    *   Path `/*` -> Origin `frontend-group`
    *   Path `/api/*` -> Origin `backend-group`
    *   Path `/sse` (or /mcp/*) -> Origin `mcp-group`

This structure completely replaces the need for Nginx in the cloud, as Front Door handles the routing logic.
