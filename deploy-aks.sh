#!/bin/bash
set -e

# --- Configuration ---
RESOURCE_GROUP="docxai-rg"
LOCATION="westeurope"
ACR_NAME="docxaicr"
AKS_CLUSTER="docxai-cluster"

# Load OpenAI key from .env if available
if [ -f .env ]; then
    export $(grep OPENAI_API_KEY .env | xargs)
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set. Please set it in your .env file or environment."
    exit 1
fi

echo "🚀 Starting DocxAI Automated AKS Deployment..."

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
echo "🔨 Building and Pushing Docker Images (Platform: linux/amd64)..."
docker build --platform linux/amd64 -f Dockerfile.mcp -t $ACR_URL/docxai-mcp:latest .
docker push $ACR_URL/docxai-mcp:latest

docker build --platform linux/amd64 -f Dockerfile.frontend -t $ACR_URL/docxai-frontend:latest .
docker push $ACR_URL/docxai-frontend:latest

docker build --platform linux/amd64 -f Dockerfile.nginx -t $ACR_URL/docxai-nginx:latest .
docker push $ACR_URL/docxai-nginx:latest

# 4. AKS Cluster Setup
echo "☸️ Setting up AKS Cluster..."
if ! az aks show --name $AKS_CLUSTER --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "   -> Creating AKS Cluster (this may take 5-10 minutes)..."
    az aks create \
        --resource-group $RESOURCE_GROUP \
        --name $AKS_CLUSTER \
        --node-count 2 \
        --generate-ssh-keys \
        --attach-acr $ACR_NAME \
        --vm-set-type VirtualMachineScaleSets \
        --load-balancer-sku standard \
        --node-vm-size Standard_B2ms
else
    echo "   -> Cluster already exists."
fi

# 5. Get AKS Credentials
echo "🔑 Getting AKS credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER --overwrite-existing

# 6. Create Kubernetes Secret
echo "🔒 Creating Kubernetes Secret..."
kubectl create secret generic docxai-secrets \
    --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

# 7. Apply Manifests
echo "📄 Applying Kubernetes Manifests..."
# Use envsubst to replace ACR_URL in the manifest
export ACR_URL=$ACR_URL
envsubst < k8s-deployment.yaml | kubectl apply -f -

echo "✅ AKS Deployment Initiated!"
echo "⏳ Waiting for Nginx Service Public IP..."
sleep 10
kubectl get service nginx-service
