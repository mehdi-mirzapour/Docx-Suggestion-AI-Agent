# 🚀 Azure Deployment Guide - DocxAI

This document provides a comprehensive guide for deploying the DocxAI application to Azure using **3 Separate App Services** behind **Azure Front Door**.

## 🏗️ Architecture Overview

```
       [Azure Front Door] (https://docxai.azurefd.net)
              │
    ┌─────────┼──────────────┐
    ▼         ▼              ▼
[Frontend] [Backend API]   [MCP Server]
(Port 80)    (Port 8787)   (Port 8787)
```

**Names used in this guide:**
- **Resource Group:** `docxai-rg`
- **Region:** `West Europe`
- **ACR Name:** `docxaicr` (Verified Unique)
- **Services:** `docxai-frontend`, `docxai-backend`, `docxai-mcp`

---

## 📋 Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Infrastructure Setup (RG & ACR)](#2-infrastructure-setup)
3. [Build & Push Images](#3-build--push-images)
4. [Deploy App Services](#4-deploy-app-services)
5. [Configure Settings & Ports](#5-configure-settings--ports)
6. [Set Up Azure Front Door](#6-set-up-azure-front-door)

---

## 1. Prerequisites

### Azure CLI Login
```bash
az login
az account set --subscription "<your-subscription-id>"
```

---

## 2. Infrastructure Setup
**Goal:** Create a Resource Group and an Azure Container Registry (ACR).

### 🔹 Option A: Azure Portal (GUI)
1.  Go to **Resource groups** -> **Create**.
    *   Name: `docxai-rg`
    *   Region: `West Europe`
    *   Click **Review + create** -> **Create**.
2.  Go to **Container registries** -> **Create**.
    *   Resource Group: `docxai-rg`
    *   Registry Name: `docxaicr`
    *   SKU: `Basic`
    *   Click **Review + create** -> **Create**.
3.  Once created, go to the Registry -> **Settings** -> **Access keys**.
    *   Enable **Admin user**.
    *   Copy the **Login server** (e.g., `docxaicr.azurecr.io`) and **Password**.

### 🔹 Option B: Azure CLI
```bash
# 1. Resource Group
az group create --name docxai-rg --location westeurope

# 2. Container Registry (ACR)
az acr create --resource-group docxai-rg --name docxaicr --sku Basic --admin-enabled true

# Login locally
az acr login --name docxaicr
```

### 🔹 Option C: Terraform
```hcl
resource "azurerm_resource_group" "docxai" {
  name     = "docxai-rg"
  location = "West Europe"
}

resource "azurerm_container_registry" "acr" {
  name                = "docxaicr"
  resource_group_name = azurerm_resource_group.docxai.name
  location            = azurerm_resource_group.docxai.location
  sku                 = "Basic"
  admin_enabled       = true
}
```

---

## 3. Build & Push Images
*(This step must be done via CLI)*

```bash
export ACR_NAME=docxaicr

# 1. Frontend
docker build -f Dockerfile.frontend -t $ACR_NAME.azurecr.io/docxai-frontend:latest .
docker push $ACR_NAME.azurecr.io/docxai-frontend:latest

# 2. Backend
docker build -f Dockerfile.backend -t $ACR_NAME.azurecr.io/docxai-backend:latest .
docker push $ACR_NAME.azurecr.io/docxai-backend:latest

# 3. MCP (Critical for ChatGPT)
docker build -f Dockerfile.mcp -t $ACR_NAME.azurecr.io/docxai-mcp:latest .
docker push $ACR_NAME.azurecr.io/docxai-mcp:latest
```

---

## 4. Deploy App Services
**Goal:** Create an App Service Plan and 3 empty Web Apps (Containers).

### 🔹 Option A: Azure Portal
1.  **Create App Service Plan**:
    *   Search "App Service plans" -> Create.
    *   Resource Group: `docxai-rg`.
    *   Name: `docxai-plan`.
    *   OS: **Linux**.
    *   Pricing Tier: **B1**.
2.  **Create 3 Web Apps** (Repeat for `docxai-frontend`, `docxai-backend`, `docxai-mcp`):
    *   Search "App Services" -> Create -> **Web App**.
    *   Name: e.g., `docxai-frontend`.
    *   Publish: **Container**.
    *   Plan: `docxai-plan`.
    *   **Container Tab**:
        *   Image Source: **Azure Container Registry**.
        *   Registry: `docxaicr`.
        *   Image: `docxai-frontend`.
        *   Tag: `latest`.

### 🔹 Option B: Azure CLI
```bash
# Plan
az appservice plan create --name docxai-plan --resource-group docxai-rg --sku B1 --is-linux

# Web Apps
az webapp create --resource-group docxai-rg --plan docxai-plan --name docxai-frontend --deployment-container-image-name docxaicr.azurecr.io/docxai-frontend:latest
az webapp create --resource-group docxai-rg --plan docxai-plan --name docxai-backend --deployment-container-image-name docxaicr.azurecr.io/docxai-backend:latest
az webapp create --resource-group docxai-rg --plan docxai-plan --name docxai-mcp --deployment-container-image-name docxaicr.azurecr.io/docxai-mcp:latest
```

### 🔹 Option C: Terraform
```hcl
resource "azurerm_service_plan" "plan" {
  name                = "docxai-plan"
  resource_group_name = azurerm_resource_group.docxai.name
  location            = azurerm_resource_group.docxai.location
  os_type             = "Linux"
  sku_name            = "B1"
}

resource "azurerm_linux_web_app" "frontend" {
  name                = "docxai-frontend"
  resource_group_name = azurerm_resource_group.docxai.name
  location            = azurerm_resource_group.docxai.location
  service_plan_id     = azurerm_service_plan.plan.id
  site_config {
    application_stack {
      docker_image_name   = "docxaicr.azurecr.io/docxai-frontend:latest"
      docker_registry_url = "https://docxaicr.azurecr.io"
    }
  }
}
# (Repeat block for backend and mcp resources)
```

---

## 5. Configure Settings & Ports

### 🔹 Option A: Azure Portal
1.  Go to each App Service -> **Settings** -> **Configuration**.
2.  **Frontend**: No changes needed (Port 80 is default).
3.  **Backend** & **MCP**:
    *   Click **New application setting**.
    *   Name: `WEBSITES_PORT`, Value: `8787`
    *   Name: `OPENAI_API_KEY`, Value: `<paste-key-here>`
    *   Click **Save**.

### 🔹 Option B: Azure CLI
```bash
export ACR_NAME=docxaicr
export ACR_PASS=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Link Credentials (for all 3)
az webapp config container set --name docxai-frontend --resource-group docxai-rg --container-registry-url https://$ACR_NAME.azurecr.io --container-registry-user $ACR_NAME --container-registry-password $ACR_PASS
az webapp config container set --name docxai-backend --resource-group docxai-rg --container-registry-url https://$ACR_NAME.azurecr.io --container-registry-user $ACR_NAME --container-registry-password $ACR_PASS
az webapp config container set --name docxai-mcp --resource-group docxai-rg --container-registry-url https://$ACR_NAME.azurecr.io --container-registry-user $ACR_NAME --container-registry-password $ACR_PASS

# Configure Ports
az webapp config appsettings set --name docxai-frontend --resource-group docxai-rg --settings WEBSITES_PORT=80
az webapp config appsettings set --name docxai-backend --resource-group docxai-rg --settings WEBSITES_PORT=8787 OPENAI_API_KEY="your-key"
az webapp config appsettings set --name docxai-mcp --resource-group docxai-rg --settings WEBSITES_PORT=8787 OPENAI_API_KEY="your-key"
```

### 🔹 Option C: Terraform
```hcl
resource "azurerm_linux_web_app" "backend" {
  # ... (other config) ...
  app_settings = {
    "WEBSITES_PORT"                   = "8787"
    "OPENAI_API_KEY"                  = "your-key"
    "DOCKER_REGISTRY_SERVER_URL"      = "https://docxaicr.azurecr.io"
    "DOCKER_REGISTRY_SERVER_USERNAME" = "docxaicr"
    "DOCKER_REGISTRY_SERVER_PASSWORD" = "<acr-password>"
  }
}
```

---

## 6. Set Up Azure Front Door

### 🔹 Option A: Azure Portal
1.  Search **Front Door and CDN profiles** -> Create -> **Azure Front Door (Standard)**.
2.  **Endpoint**: Name it `docxai-main`.
3.  **Routes** (Add 3 routes):
    *   **Frontend**: Path `/*`, Origin Host `docxai-frontend.azurewebsites.net`.
    *   **API**: Path `/api/*`, Origin Host `docxai-backend.azurewebsites.net`.
    *   **MCP**: Path `/sse`, Origin Host `docxai-mcp.azurewebsites.net`.
4.  Create and wait for deployment.

### 🔹 Option B: Azure CLI
```bash
# Create Profile
az afd profile create --profile-name docxai-fd --resource-group docxai-rg --sku Standard_AzureFrontDoor

# Create Endpoint
az afd endpoint create --resource-group docxai-rg --profile-name docxai-fd --endpoint-name docxai-main

# Add Origins (Groups)
az afd origin-group create --resource-group docxai-rg --profile-name docxai-fd --origin-group-name frontend-group
az afd origin create --resource-group docxai-rg --profile-name docxai-fd --origin-group-name frontend-group --origin-name frontend --host-name docxai-frontend.azurewebsites.net

az afd origin-group create --resource-group docxai-rg --profile-name docxai-fd --origin-group-name backend-group
az afd origin create --resource-group docxai-rg --profile-name docxai-fd --origin-group-name backend-group --origin-name backend --host-name docxai-backend.azurewebsites.net

az afd origin-group create --resource-group docxai-rg --profile-name docxai-fd --origin-group-name mcp-group
# Important: Check usage of /sse path for health probes if needed
az afd origin create --resource-group docxai-rg --profile-name docxai-fd --origin-group-name mcp-group --origin-name mcp --host-name docxai-mcp.azurewebsites.net

# Add Routes
az afd route create --resource-group docxai-rg --profile-name docxai-fd --endpoint-name docxai-main --route-name frontend-route --origin-group frontend-group --supported-protocols Http Https --link-to-default-domain Enabled --patterns-to-match "/*"
az afd route create --resource-group docxai-rg --profile-name docxai-fd --endpoint-name docxai-main --route-name backend-route --origin-group backend-group --supported-protocols Http Https --link-to-default-domain Enabled --patterns-to-match "/api/*"
az afd route create --resource-group docxai-rg --profile-name docxai-fd --endpoint-name docxai-main --route-name mcp-route --origin-group mcp-group --supported-protocols Http Https --link-to-default-domain Enabled --patterns-to-match "/sse"
```

### 🔹 Option C: Terraform
*Detailed Front Door Terraform configuration requires defining Profiles, Endpoints, Origin Groups, Origins, and Routes resources similar to the `azurerm_cdn_frontdoor_*` family.*
