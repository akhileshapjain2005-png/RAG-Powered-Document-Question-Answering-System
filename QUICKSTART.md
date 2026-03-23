# Quick Start Guide - RAG-DocQA

Get up and running with RAG-DocQA: AI-Powered Document Question Answering System in 5 minutes!

## Prerequisites

- Python 3.11+ and Node.js 18+ installed
- OpenAI API key (get one at https://platform.openai.com/api-keys)

## Quick Setup

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_api_key_here
uvicorn app.main:app --reload
```

Backend will run on http://localhost:8000

### 2. Frontend Setup (New Terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend will run on http://localhost:3000

### 3. Use the Application

1. Open http://localhost:3000 in your browser
2. Go to "Documents" tab
3. Upload a PDF, DOCX, or Markdown file
4. Go to "Chat" tab
5. Ask questions about your document!

## Docker Quick Start

```bash
# Create .env file from template
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (and optional API_KEY)

# Start services
docker-compose up -d

# Access at http://localhost:3000
# API is available at http://localhost:3000/api (nginx proxies to backend)
```

## Example Questions

- "What is this document about?"
- "Summarize the main points"
- "What are the key findings?"
- "Explain the methodology used"

## Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (should be 3.11+)
- Ensure virtual environment is activated
- Check OPENAI_API_KEY is set

**Frontend won't start:**
- Check Node version: `node --version` (should be 18+)
- Delete `node_modules` and run `npm install` again

**Documents not processing:**
- Check file format is supported (PDF, DOCX, MD, TXT)
- Check backend logs for errors
- Ensure backend is running on port 8000

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check out [API documentation](http://localhost:3000/api/docs) when using Docker Compose
- Explore the code structure in `backend/app/` and `frontend/src/`
