#!/usr/bin/env bash
# Shell Deployment helper script for GCP Cloud Run
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE_NAME="demandguard-api"
REPO_NAME="demandguard-repo"
IMAGE_TAG="latest"

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: GCP_PROJECT_ID is not set. Provide as argument or export GCP_PROJECT_ID."
    echo "Usage: ./scripts/deploy_cloud_run.sh <PROJECT_ID>"
    exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "=== DemandGuard Cloud Run Deployment ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region:     ${REGION}"
echo "Image URI:  ${IMAGE_URI}"

echo -e "\nStep 1: Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo -e "\nStep 2: Building and pushing Docker image..."
docker build -t "${IMAGE_URI}" .
docker push "${IMAGE_URI}"

echo -e "\nStep 3: Deploying service to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_URI}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 2 \
    --port 8000

echo -e "\nDeployment completed successfully!"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')
echo "Live API Docs: ${SERVICE_URL}/docs"
