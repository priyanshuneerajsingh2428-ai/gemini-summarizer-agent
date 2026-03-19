#!/usr/bin/env bash
# =============================================================================
#  deploy.sh — One-command deployment to Google Cloud Run
#
#  Usage:
#    export GCP_PROJECT_ID="your-project-id"
#    bash deploy.sh
#
#  Requirements: gcloud CLI, Docker Desktop (running)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Config — override via environment variables
# ---------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:?ERROR: Set GCP_PROJECT_ID environment variable}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="gemini-summarizer-agent"
REPO_NAME="adk-agents"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:latest"

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       ADK Summarizer Agent — Cloud Run Deployment        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Service : ${SERVICE_NAME}"
echo "  Image   : ${IMAGE}"
echo ""

# ---------------------------------------------------------------------------
# Step 1 — Enable required APIs
# ---------------------------------------------------------------------------
echo "▶ [1/6] Enabling required Google Cloud APIs…"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  --project="${PROJECT_ID}" \
  --quiet
echo "   ✅ APIs enabled."

# ---------------------------------------------------------------------------
# Step 2 — Create Artifact Registry repo (idempotent)
# ---------------------------------------------------------------------------
echo "▶ [2/6] Creating Artifact Registry repository…"
gcloud artifacts repositories create "${REPO_NAME}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet 2>/dev/null \
  && echo "   ✅ Repository created." \
  || echo "   ℹ️  Repository already exists — skipping."

# ---------------------------------------------------------------------------
# Step 3 — Auth Docker → Artifact Registry
# ---------------------------------------------------------------------------
echo "▶ [3/6] Configuring Docker authentication…"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
echo "   ✅ Docker auth configured."

# ---------------------------------------------------------------------------
# Step 4 — Build image
# ---------------------------------------------------------------------------
echo "▶ [4/6] Building Docker image (linux/amd64)…"
docker build --platform linux/amd64 -t "${IMAGE}" .
echo "   ✅ Image built."

# ---------------------------------------------------------------------------
# Step 5 — Push image
# ---------------------------------------------------------------------------
echo "▶ [5/6] Pushing image to Artifact Registry…"
docker push "${IMAGE}"
echo "   ✅ Image pushed."

# ---------------------------------------------------------------------------
# Step 6 — Deploy to Cloud Run
# ---------------------------------------------------------------------------
echo "▶ [6/6] Deploying to Cloud Run…"
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=60s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --project="${PROJECT_ID}" \
  --quiet

# ---------------------------------------------------------------------------
# Done — print URL
# ---------------------------------------------------------------------------
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                  🎉 Deployment Complete!                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Cloud Run URL : ${SERVICE_URL}"
echo ""
echo "  Quick test:"
echo ""
echo "  curl -X POST ${SERVICE_URL}/summarize \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"text\": \"Your text here.\", \"style\": \"bullet\"}'"
echo ""
echo "  Swagger UI    : ${SERVICE_URL}/docs"
echo "  Agent Card    : ${SERVICE_URL}/agent-card"
echo ""
