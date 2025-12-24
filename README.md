## Azure RAG MVP – Technical Guide

Full-stack Retrieval Augmented Generation system that ingests PDF/MD/TXT documents into Azure Blob Storage, processes them into Azure AI Search with hybrid + semantic retrieval, and serves GPT-4o backed answers through a React TypeScript frontend and a FastAPI backend. The solution targets Azure Container Apps for deployment and uses Azure OpenAI for both completions and embeddings.

## 1. Mission Overview
- **Goal**: Deliver an end-to-end Retrieval Augmented Generation (RAG) solution that ingests enterprise documents, indexes them with Azure AI Search, and serves grounded answers through a GPT-4o powered chat experience.
- **Scope**: React/Vite TypeScript frontend, FastAPI backend, LangChain orchestration, Azure Storage + AI Search + OpenAI, deployable to Azure Container Apps (ACA).
- **User Flow**: Upload PDFs/Markdown/TXT → launch processing run → ask questions with cited passages, latency, and confidence indicators.

## 1.1 Application Capabilities
- **Upload & Validation**: Frontend streams PDF/MD/TXT files to `/api/files/upload`, enforces MIME types, and surfaces success/error states.
- **Processing Orchestration**: Backend `processing_manager` coordinates chunking, embedding, and indexing, exposing live progress metrics the UI polls.
- **Chat Experience**: React chat panel keeps full conversation context, displays latency/confidence, and surfaces collapsible citations/snippets returned from `run_rag()`.
- **Citations & Grounding**: RAG pipeline prioritizes top-source chunks, enforces dynamic score thresholds, and ensures every answer has at least one reference.
- **Operations Visibility**: `/health` endpoint, progress meters, and structured logging (FastAPI + Uvicorn) support deployment health checks in ACA or local dev.

## 2. System Architecture
| Layer | Responsibilities | Key Technologies |
| --- | --- | --- |
| **Frontend (frontend/)** | File uploads, processing controls, chat UI, optimistic status updates | React 18, Vite, TypeScript, TanStack Query |
| **Backend API (backend/app/)** | Upload ingress, processing orchestration, RAG chat endpoint | FastAPI, Pydantic, Uvicorn |
| **Processing & Retrieval Services** | Chunking, embedding, Azure AI Search indexing & querying | LangChain Text Splitters, Azure OpenAI, Azure AI Search SDK |
| **Data Plane** | Raw vs processed blobs, vector index storing hybrid content | Azure Blob Storage, Azure AI Search (vector + semantic) |
| **Deployment** | Containerized services running on ACA with Bicep provisioning | Docker, Azure Container Apps, Managed Identity |

High-level flow:
1. **Upload** – Files stream into the *raw* blob container via `/api/files/upload`.
2. **Process** – `/api/processing/start` launches an asynchronous job that transforms and indexes content.
3. **Retrieve** – `/api/chat/completions` executes semantic + vector search with GPT-4o assisted answers referencing the indexed chunks.

## 3. Azure Resources & AI Technologies
- **Azure Blob Storage**: Two containers (`raw-documents`, `processed-documents`) segregate pending vs. completed files. Managed Identity or connection strings enable access.
- **Azure AI Search**: Vector-enabled index (`rag-index` by default) using HNSW/search + semantic ranking (`semanticConfig`). Fields: `id`, `content`, `chunk_id`, `source_path`, `chunk_order`, `metadata`, and `embedding` (3,072 dims).
- **Azure OpenAI**:
   - `gpt-4o` deployment for chat completions (temperature 0.1, 2024-08-01-preview API).
   - `text-embedding-3-large` deployment for question + chunk embedding generation.
- **Managed Identity (optional)**: Grants the backend access to Storage/Search when API keys are not supplied.
- **Azure Container Apps**: Hosts both frontend and backend containers; parameters managed via Bicep templates under `infrastructure/`.

## 4. Core Libraries & Packages
- **Backend**: `fastapi`, `uvicorn`, `langchain`, `langchain-openai`, `langchain-text-splitters`, `azure-storage-blob`, `azure-identity`, `azure-search-documents`, `pypdf`, `pydantic-settings`.
- **Frontend**: `react`, `react-dom`, `@tanstack/react-query`, `clsx`, `vite`, `typescript`.
- **Shared Concepts**: Pydantic models enforce API contracts; TanStack Query handles polling and cache invalidation; LangChain clients wrap Azure OpenAI.

## 5. Backend Services
### 5.1 Configuration (`app/core/config.py`)
- Pydantic settings pull from `.env`, covering storage endpoints, search index name, OpenAI deployments, chunk sizes, and processing limits.
- Defaults: chunk size 1,500 chars with 200 overlap; max 25 documents per run.

### 5.2 API Surface (`app/api/routes.py`)
| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/files/upload` | POST multi-part | Save files into raw container; returns blob metadata. |
| `/api/files/recent` | GET | List latest uploads for UI display. |
| `/api/processing/start` | POST | Queue a processing job (optional document limit). |
| `/api/processing/{job_id}` | GET | Poll job progress (files discovered, chunks indexed, embeddings created). |
| `/api/chat/completions` | POST | Execute the RAG pipeline and return answer, citations, latency, confidence. |

### 5.3 Storage Service (`app/services/storage.py`)
- Uses connection string or `DefaultAzureCredential`.
- Ensures containers exist at startup; supports upload, list, download, move (copy-then-delete), and unprocessed enumeration.

### 5.4 Processing Manager (`app/services/processing.py`)
1. `start_job()` spins a UUID job, initializes progress steps, and delegates work onto a thread pool executor.
2. `_run_job()` sequence per blob:
    - Download bytes → convert to text (`app/utils/document_loader.py` with PDF parsing via `pypdf`).
    - Split with `RecursiveCharacterTextSplitter` (1500/200) to preserve semantic continuity.
    - Generate sanitized chunk IDs (`blobname-<order>`), embed chunk text in batches via `AzureOpenAIEmbeddings`.
    - Upload chunk documents to Azure AI Search (content, metadata JSON, vector) and move the source blob into the processed container.
    - Increment per-step counters for UI feedback (files processed, chunks indexed, embeddings created).
3. Errors are captured in the job status; state transitions through `queued → running → completed|failed`.

### 5.5 Retrieval & Generation (`app/services/rag.py`)
- Question embedding + semantic hybrid search: `VectorizedQuery` with `k_nearest_neighbors = top_k` combined with `search_text` for keyword + semantic ranking.
- Dynamic citation logic:
   - Rank hits by `@search.score` and lock onto the top document as the “primary.”
   - Accept chunks from the primary document until four citations or threshold satisfied.
   - Include secondary documents only if their score ≥ 60% of the top score (floor 0.2).
   - Always guarantee at least one citation even when filtering removes others.
- Build contextual prompt: join chunk texts with `---`, append citation summary, and invoke GPT-4o chat completion via `AzureChatOpenAI` wrapper.
- Response includes latency (ms), normalized confidence (capped score), and citation snippets (first 400 chars).

### 5.6 Azure AI Search Helper (`app/services/search.py`)
- Ensures index creation with vector search profiles (HNSW + ExhaustiveKnn) and a suggester for future auto-complete.
- `semantic_hybrid_search()` runs combined vector and semantic query.

### 5.7 OpenAI Client (`app/services/openai_client.py`)
- Centralizes chat + embedding clients with shared endpoint/key/deployment IDs.
- Chat prompt enforces grounding: “Answer only using the provided context.”

## 6. Frontend Experience
### 6.1 App Shell (`src/App.tsx`)
- Layout hosts upload + processing panels side-by-side with the chat panel below; header surfaces environment tagline and upload summary.

### 6.2 File Upload Panel
- Accepts PDF/MD/TXT (multiple) via `<input type="file" multiple>`.
- Uses Fetch form-data helper (`uploadDocuments`) to POST to `/api/files/upload`.
- Shows success toast text, resets file input, and calls parent callback so header can reflect pending items.

### 6.3 Processing Panel
- Leverages TanStack Query to refresh `/api/files/recent` list every 5 seconds.
- `startProcessing()` triggers backend job then persists job ID.
- `useProcessingPoll()` repeatedly hits `/api/processing/{job_id}` until completion/failure, driving the `ProgressMeter` bars.

### 6.4 Chat Panel
- Maintains conversation state (user + assistant messages) and last backend `ChatResponse`.
- Submit action posts `{question, history, top_k}` to `/api/chat/completions`.
- Displays user questions, answer bubble with latency/confidence metrics, and expandable citation drawer showing chips + snippets for each chunk.

### 6.5 Styling (`src/styles.css`)
- Glassmorphism-inspired panels, responsive layout, citation chips/cards to keep references visible without overpowering chat.

## 7. Processing & Data Lifecycle
1. **Ingestion**: Users upload via UI or direct API; files stored in raw container.
2. **Discovery**: Processing job enumerates raw blobs (optional cap) and updates `filesDiscovered` metric.
3. **Preparation**: Convert to UTF-8 text (PDF parsing via `pypdf`), chunk with overlap, sanitize IDs.
4. **Embedding**: Batch call `text-embedding-3-large` (3,072 dims) via LangChain Azure client.
5. **Indexing**: Write documents to Azure AI Search with metadata JSON for downstream citations.
6. **Archival**: Move blobs to processed container after successful ingest to avoid reprocessing.
7. **Retrieval**: Questions converted to embeddings, vector + semantic search run, context assembled.
8. **Generation**: GPT-4o responds under tight grounding instructions; citations + scores returned to UI.

## 8. Configuration & Secrets
Populate `backend/.env` (based on `.env.example`):
```
AZURE_STORAGE_ACCOUNT_URL=...
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_STORAGE_RAW_CONTAINER=raw-documents
AZURE_STORAGE_PROCESSED_CONTAINER=processed-documents
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_INDEX=rag-index
AZURE_SEARCH_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_GPT4O_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
PROCESSING_CHUNK_SIZE=1500
PROCESSING_CHUNK_OVERLAP=200
```
Frontend relies on Vite dev proxy to forward `/api` to `http://localhost:8000`; production deployments should configure environment-specific API roots.

## 9. Prerequisites
- Node.js 20+
- Python 3.11+
- Azure CLI (for deployment)
- Azure subscription with access to Azure OpenAI + AI Search preview SKUs

## 10. Local Development
### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill Azure credentials
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
The Vite dev server proxies `/api` to `http://localhost:8000`.

### Docker Compose (optional)
```bash
docker compose up --build
```

## 11. Deployment & Operations
- **Build & Push Images**
   ```powershell
   ./scripts/build-and-push.ps1 -Registry <your-registry> -Tag v1
   ```
- **Provision Azure Resources**
   ```powershell
   cd infrastructure
   az deployment group create `
      --resource-group <rg> `
      --template-file main.bicep `
      --parameters @parameters.json
   ```
   Update `parameters.json` with image tags and registry server.
- **Configure App Settings**
   - Set environment variables (storage URLs, search index, OpenAI deployments, keys) via Azure Portal/CLI for the backend Container App. Assign the managed identity access to Storage + Search if not already.
- **Smoke Test**
   - Hit the frontend Container App URL (output `frontendAppUrl`) and upload a test document, process it, then ask questions.
- **Monitoring Ideas**
   - Surface App Insights telemetry, track search latency, and add health probes per `/health` endpoint.

## 12. Testing & Validation Checklist
- Upload PDFs + Markdown to confirm parser resiliency and chunk distribution.
- Process run: verify `filesDiscovered`, `filesProcessed`, `chunksIndexed`, `embeddingsCreated` progress numbers increment.
- Chat evaluation: ask grounded questions, ensure citations reference actual documents, and inspect `confidence` vs. `@search.score`.
- Fault injection: invalid MIME upload, empty search results, Azure search/index outages (expectation is surfaced in job status errors).

## 13. Extensibility Roadmap
1. **Security**: Add Azure AD auth, user-level rate limiting, and role-based document scoping.
2. **Automation**: Trigger processing via Event Grid on blob creation instead of manual job launch.
3. **Analytics**: Persist chat transcripts + telemetry to Application Insights or Cosmos DB for evaluation.
4. **Advanced Ranking**: Blend re-ranking models, implement multi-vector fields (title vs. body), or incorporate filters (departments, tags).
5. **Evaluator Harness**: Build regression tests that compare answers vs. ground-truth sets for policy documents.

---
This guide should serve as the canonical reference for maintainers, SREs, and stakeholders who need to understand how the Azure RAG MVP is assembled, which AI services it depends on, and how to extend or operate it in production.
