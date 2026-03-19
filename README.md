# 🤖 Gemini ADK Text Summarizer Agent

> **Track 1 Submission** — Build and deploy AI agents using Gemini, ADK, and Cloud Run

A production-ready AI agent that summarizes text using **Google Agent Development Kit (ADK)** and **Gemini 2.0 Flash**, deployed as a serverless container on **Google Cloud Run**.

[![CI](https://github.com/YOUR_USERNAME/gemini-summarizer-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/gemini-summarizer-agent/actions)
![Python](https://img.shields.io/badge/python-3.12-blue)
![ADK](https://img.shields.io/badge/Google%20ADK-0.5.0-orange)
![Cloud Run](https://img.shields.io/badge/Cloud%20Run-serverless-brightgreen)

---

## 📋 Table of Contents

- [What This Agent Does](#-what-this-agent-does)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Local Development](#-local-development)
- [Step-by-Step Cloud Run Deployment](#-step-by-step-cloud-run-deployment)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Cleanup](#-cleanup)

---

## 🎯 What This Agent Does

The **Summarizer Agent** accepts any block of text via an HTTP POST request and returns:

| Field | Description |
|-------|-------------|
| `summary` | Concise summary in bullet or paragraph style |
| `word_count` | Approximate word count of the original text |
| `key_topics` | Up to 5 key topics extracted from the text |
| `sentiment` | Overall sentiment: `positive`, `neutral`, or `negative` |

**Example request:**
```bash
curl -X POST https://YOUR-SERVICE-URL/summarize \
     -H "Content-Type: application/json" \
     -d '{"text": "Artificial intelligence is transforming industries...", "style": "bullet"}'
```

**Example response:**
```json
{
  "summary": "• AI is rapidly transforming multiple industries\n• Safety and ethics concerns are growing\n• Researchers are building governance frameworks",
  "word_count": 87,
  "key_topics": ["artificial intelligence", "safety", "ethics", "governance", "machine learning"],
  "sentiment": "neutral",
  "model": "gemini-2.0-flash",
  "style": "bullet"
}
```

---

## 🏗 Architecture

```
HTTP Client
     │
     ▼
┌────────────────────────────────────┐
│         Google Cloud Run           │
│  ┌──────────────────────────────┐  │
│  │       FastAPI Server         │  │
│  │         (main.py)            │  │
│  └──────────┬───────────────────┘  │
│             │                      │
│  ┌──────────▼───────────────────┐  │
│  │       ADK Runner             │  │
│  │  (google.adk.runners)        │  │
│  └──────────┬───────────────────┘  │
│             │                      │
│  ┌──────────▼───────────────────┐  │
│  │    Summarizer Agent          │  │
│  │  (agent/agent.py)            │  │
│  │  ┌────────────────────────┐  │  │
│  │  │  summarize_text tool   │  │  │
│  │  └────────────────────────┘  │  │
│  └──────────┬───────────────────┘  │
└────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  Gemini 2.0     │
    │  Flash (API)    │
    └─────────────────┘
```

---

## 📁 Project Structure

```
gemini-summarizer-agent/
├── agent/
│   ├── __init__.py          # Package exports
│   └── agent.py             # ADK Agent + tool definition
├── tests/
│   ├── __init__.py
│   └── test_api.py          # Unit tests (mocked ADK)
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI pipeline
├── main.py                  # FastAPI server (HTTP entrypoint)
├── requirements.txt         # Python dependencies
├── Dockerfile               # Multi-stage Docker build
├── .dockerignore
├── .gitignore
├── .env.example             # Environment variable template
├── deploy.sh                # One-command Cloud Run deployment
└── test_deployed.py         # Smoke tests against live URL
```

---

## ✅ Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.12 | https://python.org |
| Docker Desktop | Latest | https://docs.docker.com/get-docker/ |
| Google Cloud SDK | Latest | https://cloud.google.com/sdk/docs/install |
| A GCP project | — | https://console.cloud.google.com |

Your GCP project must have **billing enabled**.

---

## 💻 Local Development

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/gemini-summarizer-agent.git
cd gemini-summarizer-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install pytest httpx            # for running tests
```

### 4. Set environment variables

```bash
cp .env.example .env
# Edit .env and set GOOGLE_CLOUD_PROJECT to your project ID
```

### 5. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 6. Run the server locally

```bash
python main.py
# Server starts at http://localhost:8080
```

### 7. Test locally

```bash
# Health check
curl http://localhost:8080/

# Summarize
curl -X POST http://localhost:8080/summarize \
     -H "Content-Type: application/json" \
     -d '{"text": "Your text here...", "style": "bullet"}'

# Swagger UI
open http://localhost:8080/docs
```

---

## 🚀 Step-by-Step Cloud Run Deployment

### Step 1 — Set up gcloud CLI

```bash
# Install gcloud if not already installed
# https://cloud.google.com/sdk/docs/install

# Log in
gcloud auth login

# Also authenticate for ADK/Gemini API access
gcloud auth application-default login
```

---

### Step 2 — Set your project ID

```bash
export GCP_PROJECT_ID="your-actual-project-id"
export GCP_REGION="us-central1"    # or your preferred region

# Confirm it's set correctly
echo "Project: $GCP_PROJECT_ID"
gcloud config set project $GCP_PROJECT_ID
```

---

### Step 3 — Enable required Google Cloud APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  --project=$GCP_PROJECT_ID
```

> This may take 1–2 minutes. Run it once per project.

---

### Step 4 — Create an Artifact Registry repository

```bash
gcloud artifacts repositories create adk-agents \
  --repository-format=docker \
  --location=$GCP_REGION \
  --project=$GCP_PROJECT_ID
```

---

### Step 5 — Configure Docker to push to Artifact Registry

```bash
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev
```

---

### Step 6 — Build the Docker image

```bash
# Set the full image path
export IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/adk-agents/gemini-summarizer-agent:latest"

# Build for Cloud Run (linux/amd64)
docker build --platform linux/amd64 -t $IMAGE .
```

> ⏳ First build takes ~3–5 minutes. Subsequent builds are faster due to layer caching.

---

### Step 7 — Push the image

```bash
docker push $IMAGE
```

---

### Step 8 — Deploy to Cloud Run

```bash
gcloud run deploy gemini-summarizer-agent \
  --image=$IMAGE \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=60s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID}" \
  --project=$GCP_PROJECT_ID
```

> ⏳ Deployment takes ~2–3 minutes on first run.

---

### Step 9 — Get your Cloud Run URL

```bash
gcloud run services describe gemini-summarizer-agent \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID \
  --format="value(status.url)"
```

You'll get a URL like:
```
https://gemini-summarizer-agent-xxxxxxxxxx-uc.a.run.app
```

---

### Step 10 — Test the deployment

```bash
export SERVICE_URL=$(gcloud run services describe gemini-summarizer-agent \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID \
  --format="value(status.url)")

# Health check
curl $SERVICE_URL/

# Summarize text
curl -X POST $SERVICE_URL/summarize \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Artificial intelligence is transforming industries at an unprecedented pace. Machine learning models are being embedded into critical systems, raising important questions about safety and ethics.",
       "style": "bullet"
     }'

# Run full smoke test suite
python test_deployed.py --url $SERVICE_URL
```

---

### ⚡ One-Command Deployment (Alternative)

```bash
export GCP_PROJECT_ID="your-project-id"
bash deploy.sh
```

The `deploy.sh` script runs all 6 steps automatically.

---

## 📡 API Reference

### `GET /`

Health check endpoint (Cloud Run liveness probe).

**Response:**
```json
{"status": "ok", "agent": "summarizer_agent", "model": "gemini-2.0-flash", "version": "1.0.0"}
```

---

### `GET /agent-card`

A2A-compatible agent card — lets other ADK agents discover and use this agent as a sub-agent.

---

### `POST /summarize`

Run the summarization agent.

**Request body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | ✅ | — | Text to summarize (min 10 chars) |
| `style` | string | ❌ | `bullet` | `bullet` or `paragraph` |
| `user_id` | string | ❌ | `anonymous` | Session user identifier |
| `session_id` | string | ❌ | `session-001` | Session identifier |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | The generated summary |
| `word_count` | integer | Approximate original word count |
| `key_topics` | string[] | Up to 5 key topics |
| `sentiment` | string | `positive`, `neutral`, or `negative` |
| `model` | string | Model used (`gemini-2.0-flash`) |
| `style` | string | Style used (`bullet` or `paragraph`) |

**Swagger UI:** `https://YOUR-SERVICE-URL/docs`

---

## 🧪 Testing

### Unit tests (no GCP credentials required)

```bash
pytest tests/ -v
```

### Smoke tests against live deployment

```bash
python test_deployed.py --url https://YOUR-CLOUD-RUN-URL
```

---

## 🧹 Cleanup

To avoid ongoing charges, delete the Cloud Run service and Artifact Registry image:

```bash
# Delete Cloud Run service
gcloud run services delete gemini-summarizer-agent \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# Delete Artifact Registry repository
gcloud artifacts repositories delete adk-agents \
  --location=$GCP_REGION \
  --project=$GCP_PROJECT_ID
```

---

## 📚 References

- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- [Build and deploy an ADK agent on Cloud Run — Codelab](https://codelabs.developers.google.com/codelabs/build-deploy-adk-agent-cloud-run)
- [Building AI Agents with ADK: The Foundation — Codelab](https://codelabs.developers.google.com/codelabs/building-ai-agents-with-adk)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)

---

## 🪪 License

MIT License — see [LICENSE](LICENSE) for details.
