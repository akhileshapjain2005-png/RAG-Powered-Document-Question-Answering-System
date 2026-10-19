# RAG-DocQA: AI-Powered Document Question Answering System

An intelligent document question-answering system built with RAG (Retrieval-Augmented Generation) architecture. Upload documents, ask questions, and get AI-powered answers with source citations. Built with FastAPI, React, ChromaDB, Sentence Transformers, and Ollama for local LLM inference.

## 🚀 Features

- **Document Processing**: Support for PDF, DOCX, Markdown, and TXT files
- **Intelligent Chunking**: Automatic text chunking with overlap for better context
- **Vector Search**: Semantic search using embeddings and ChromaDB
- **LLM Integration**: Local language-model inference through Ollama
- **Streaming Responses**: Real-time streaming of AI responses
- **Source Citations**: Track which documents and chunks were used for answers
- **Modern UI**: Beautiful, responsive React frontend
- **RESTful API**: FastAPI backend with comprehensive endpoints
- **Docker Support**: Easy deployment with Docker Compose

## 📋 Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Enterprise](#enterprise-hardening)
- [Security](SECURITY.md)
- [Development](#development)
- [Future Improvements](#future-improvements)

## 🏗️ Architecture

The system follows a RAG (Retrieval-Augmented Generation) architecture:

```
┌─────────────┐
│   Frontend  │  React Application
│  (React)    │  - Document Upload
└──────┬──────┘  - Chat Interface
       │         - Document Management
       │ HTTP
       ▼
┌─────────────┐
│   Backend   │  FastAPI Application
│  (FastAPI)  │  - REST API
└──────┬──────┘  - Document Processing
       │
       ├─────────┐
       │         │
       ▼         ▼
┌──────────┐  ┌──────────────┐
│ Document │  │   Embedding  │
│Processor │  │    Model     │
└────┬─────┘  └──────┬───────┘
     │               │
     │               ▼
     │         ┌──────────────┐
     │         │ Vector Store │
     │         │  (ChromaDB)  │
     │         └──────┬───────┘
     │                │
     └────────────────┘
              │
              ▼
       ┌──────────────┐
       │  LLM Service │
       │   (Ollama)   │
       └──────────────┘
```

### Data Flow

1. **Document Upload**: User uploads a document through the frontend
2. **Text Extraction**: Backend extracts text based on file type (PDF, DOCX, etc.)
3. **Chunking**: Text is split into overlapping chunks for better context
4. **Embedding**: Each chunk is converted to a vector using sentence transformers
5. **Storage**: Embeddings and metadata are stored in ChromaDB vector database
6. **Query Processing**: User question is embedded and used to search similar chunks
7. **Context Retrieval**: Top-K most relevant chunks are retrieved
8. **Answer Generation**: LLM generates answer based on retrieved context
9. **Response**: Answer with source citations is returned to the user

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **sentence-transformers**: Embedding generation
- **ChromaDB**: Vector database for similarity search
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX text extraction
- **Ollama**: Local LLM runtime for answer generation

### Frontend
- **React**: UI framework
- **Vite**: Build tool and dev server
- **Axios**: HTTP client
- **Modern CSS**: Responsive design with gradients

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

## 📦 Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (optional, for containerized deployment)
- Ollama installed and running (https://ollama.com/download)

Ollama runs the language model on your computer. After downloading the model, inference can run locally; internet access is needed for initial model downloads and updates.

## 🔧 Installation

### Option 1: Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd portproj
```

2. Create or update your `.env` file with the Ollama settings shown in the Configuration section. Do not add an OpenAI key when using Ollama.

3. Start the services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API (proxied): http://localhost:3000/api
- API Docs: http://localhost:3000/api/docs

### Option 2: Local Development

#### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows PowerShell (if venv is in the repository root): ..\venv\Scripts\Activate.ps1
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure `backend/.env` with the local Ollama settings:
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_STORE_PATH=./vector_store
```

Download the model and verify it is available:
```powershell
ollama pull llama3.2:latest
ollama list
```

Keep Ollama running while the application is in use. Ensure the backend loads the `.env` file and passes these settings to the LLM service.

5. Run the server:
```bash
uvicorn app.main:app --reload
```

#### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

4. Access the application at http://localhost:3000

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Runtime environment name (`development`, `production`, etc.) | `development` locally; `production` in compose |
| `ENABLE_API_DOCS` | Expose `/docs`, `/redoc`, `/openapi.json` | `false` in production by default |
| `LLM_PROVIDER` | LLM provider | `ollama` |
| `LLM_MODEL` | Ollama model name | `llama3.2:latest` |
| `OLLAMA_BASE_URL` | Ollama HTTP API URL | `http://localhost:11434` |
| `EMBEDDING_MODEL` | Embedding model name | `sentence-transformers/all-MiniLM-L6-v2` |
| `VECTOR_STORE_PATH` | Path to ChromaDB storage | `./vector_store` (match this to the path used by your code) |
| `VITE_API_URL` | Backend API URL for frontend | `/api` (recommended behind nginx) |
| `API_KEY` | Optional API key required for protected backend endpoints | Empty (disabled) |
| `API_KEYS` | Optional comma-separated additional API keys | Empty |
| `API_KEY_HEADER_NAME` | Header used for API key auth | `X-API-Key` |
| `MAX_UPLOAD_BYTES` | Max upload size in bytes | `10485760` (10MB) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins | `http://localhost:3000` |
| `RATE_LIMIT_ENABLED` | Enable API rate limiting | `true` |
| `RATE_LIMIT_DEFAULT` | Default limiter | `200/minute` |
| `RATE_LIMIT_UPLOAD` | Upload endpoint limit | `20/hour` |
| `RATE_LIMIT_ASK` | Ask endpoints limit | `120/hour` |
| `RATE_LIMIT_READ` | Read endpoints limit | `600/hour` |
| `AUTH_MODE` | `anonymous`, `api_key`, `jwt`, `jwt_or_api_key` | `jwt_or_api_key` |
| `JWT_JWKS_URL` | OIDC JWKS URL (Auth0/Azure AD/Okta/Keycloak) | Empty |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Optional JWT validation | Empty |
| `STATS_ALLOWED_ROLES` | Comma-separated roles allowed to call `GET /stats` | Empty (any authenticated caller) |
| `ENABLE_METRICS` | Expose Prometheus metrics at `GET /metrics` | `true` |

### Enterprise hardening

For SSO/OIDC, tenant claims, RBAC on stats, audit JSON logs, and Prometheus metrics, see **[ENTERPRISE.md](ENTERPRISE.md)**.

### Ollama (Local LLM) Setup

Install Ollama from <https://ollama.com/download>, then run:

```powershell
ollama pull llama3.2:latest
ollama list
ollama run llama3.2:latest
```

Type a test prompt to confirm the model responds, then enter `/bye` to exit. Ollama's default local API URL is `http://localhost:11434`.

For local development, set these values in `backend/.env`:

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434
```

The backend's LLM service must support the `ollama` provider and read these settings at startup. When the backend runs inside Docker, `localhost` points to the backend container, not the host machine; configure the Ollama host address and Docker networking accordingly.

### Supported File Types

- PDF (`.pdf`)
- Microsoft Word (`.docx`, `.doc`)
- Markdown (`.md`, `.markdown`)
- Plain Text (`.txt`)

## 📖 Usage

### Uploading Documents

1. Navigate to the "Documents" tab
2. Drag and drop a file or click to select
3. Wait for processing (document is chunked and embedded)
4. Document appears in the list

### Asking Questions

1. Navigate to the "Chat" tab
2. Type your question in the input box
3. Click "Send" or press Enter
4. View the answer with source citations

### Selecting Documents

- Check documents in the Documents tab to limit search scope
- Uncheck to search across all documents

### Streaming Responses

- Click "Stream" button for real-time token streaming
- Useful for longer responses

## 📡 API Documentation

### Endpoints

#### Document Management

- `POST /api/documents/upload` - Upload a document
- `GET /api/documents` - List all documents
- `GET /api/documents/{document_id}` - Get document details
- `DELETE /api/documents/{document_id}` - Delete a document

#### Question Answering

- `POST /api/ask` - Ask a question (returns full answer)
- `POST /api/ask/stream` - Ask a question (streaming response)

#### System

- `GET /api/stats` - Get system statistics
- `GET /api/health` - Health check

**Note:** The stable HTTP contract is **`/api/v1/*`**. The UI and nginx dev/proxy setup call **`/api/*`**, which is rewritten to **`/api/v1/*`**.

### Example API Calls

#### Upload Document
```bash
curl -X POST "http://localhost:3000/api/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

#### Ask Question
```bash
curl -X POST "http://localhost:3000/api/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your_api_key_if_enabled>" \
  -d '{
    "question": "What is this document about?",
    "top_k": 5
  }'
```

**Tip:** For `/api/ask`, use the real document UUID returned by the upload endpoint in `document_ids`. Leaving the Swagger placeholder value `"string"` will fail UUID validation with `422 Unprocessable Entity`.

#### Get Statistics
```bash
curl "http://localhost:3000/api/stats"
```

API documentation is available at http://localhost:3000/api/docs when `ENABLE_API_DOCS=true` (disabled by default in the provided compose file).

## 🚢 Deployment

### Production Deployment

1. **Build Docker images**:
```bash
docker-compose build
```

2. **Set production environment variables**:
```bash
# Edit docker-compose.yml or use .env file
```

**Recommended production settings**
- Set `API_KEY` (and optionally `API_KEYS`) so the API is not anonymously accessible.
- Set `ENV=production` and keep `ENABLE_API_DOCS=false` unless you explicitly want Swagger exposed.
- Keep `CORS_ALLOWED_ORIGINS` limited to your real frontend origin(s).
- Prefer same-origin API calls (`VITE_API_URL=/api`) and avoid baking secrets into the frontend bundle.

3. **Run in production mode**:
```bash
docker-compose up -d
```

### Cloud Deployment

#### AWS
- Deploy backend to AWS ECS or EC2
- Use RDS or S3 for vector store persistence
- Deploy frontend to S3 + CloudFront

#### GCP
- Deploy backend to Cloud Run
- Use Cloud Storage for vector store
- Deploy frontend to Firebase Hosting

#### Azure
- Deploy backend to Azure Container Instances
- Use Azure Blob Storage for vector store
- Deploy frontend to Azure Static Web Apps

### Environment-Specific Considerations

- **Vector Store**: Consider using managed vector databases (Pinecone, Weaviate) for production
- **LLM**: Use API keys from environment variables, never commit them
- **Scaling**: Use load balancers and multiple backend instances
- **Monitoring**: Add logging and monitoring (e.g., Prometheus, Grafana)

## 💻 Development

### Project Structure

```
portproj/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # ML models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utilities
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── services/     # API clients
│   ├── package.json
│   └── Dockerfile
├── ml/
│   ├── models/           # Model files
│   ├── embeddings/       # Embedding scripts
│   └── notebooks/        # Jupyter notebooks
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
# Backend tests (when implemented)
cd backend
pytest

# Frontend tests (when implemented)
cd frontend
npm test
```

### Code Style

- Backend: Follow PEP 8, use type hints
- Frontend: Follow ESLint rules, use functional components

## 🔮 Future Improvements

### Short-term
- [ ] Add user authentication and multi-user support (API key tenant isolation is implemented; user accounts are not)
- [ ] Implement document versioning
- [ ] Add support for more file types (Excel, PowerPoint)
- [ ] Improve chunking strategies (semantic chunking)
- [ ] Add conversation history persistence
- [ ] Implement document search/filtering

### Medium-term
- [ ] Support for multiple LLM providers (Anthropic, Cohere)
- [ ] Fine-tuned embedding models
- [ ] Advanced RAG techniques (re-ranking, query expansion)
- [ ] Export conversations to PDF/Markdown
- [ ] Batch document processing
- [x] API rate limiting and API-key authentication

### Long-term
- [ ] Multi-modal support (images, tables in documents)
- [ ] Real-time collaboration features
- [ ] Advanced analytics and insights
- [ ] Custom model fine-tuning interface
- [ ] Integration with cloud storage (S3, Google Drive)
- [ ] Mobile app support

## 📊 Performance Metrics

- **Embedding Generation**: ~100-200ms per chunk (CPU)
- **Vector Search**: ~10-50ms for top-5 results
- **LLM Response**: Depends on the Ollama model, prompt/context length, and available hardware
- **Document Processing**: ~1-5s per document (depends on size)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔍 Keywords & Search Terms

**RAG**, **Retrieval-Augmented Generation**, **Document Q&A**, **Document Question Answering**, **AI Document Assistant**, **LLM Integration**, **Ollama**, **Vector Database**, **ChromaDB**, **FastAPI**, **React**, **Embeddings**, **Semantic Search**, **Document Processing**, **PDF Q&A**, **Document Chatbot**, **RAG Implementation**, **AI-Powered Search**, **Document Intelligence**, **Natural Language Processing**, **NLP**, **Machine Learning**, **ML Portfolio Project**

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Embeddings powered by [sentence-transformers](https://www.sbert.net/)
- Vector database: [ChromaDB](https://www.trychroma.com/)
- UI framework: [React](https://react.dev/)


---

**Note**: This is a portfolio project demonstrating RAG architecture, full-stack development, and ML integration. For production use, consider additional security, scalability, and monitoring features.