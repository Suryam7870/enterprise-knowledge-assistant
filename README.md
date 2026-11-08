# Simple Enterprise Knowledge Assistant

A beginner-friendly RAG application. Upload text-based PDFs, split their text into chunks, create embeddings, store them in PostgreSQL with pgvector, retrieve the top matching chunks, and ask a local Ollama model to answer using those chunks.

## Simple architecture

```text
PDF Upload                         User Question
    |                                   |
    v                                   v
Extract text                       FastAPI /ask
    |                                   |
    v                                   v
Split into chunks                Create question embedding
    |                                   |
    v                                   v
Create embeddings  ------------> PostgreSQL + pgvector
    |                                   |
    v                                   v
Store chunks                     Retrieve top 3 chunks
                                        |
                                        v
                                  Build context prompt
                                        |
                                        v
                                  Ollama local LLM
                                        |
                                        v
                                  Answer + sources
```

## Requirements

- Python 3.10 or newer
- PostgreSQL
- pgvector extension installed in PostgreSQL
- Ollama installed and running
- A local Ollama model, e.g. `llama3.2:3b`

This starter is intentionally a **single-user local learning project**. It does not include JWT authentication, multi-user permissions, hybrid search, reranking, or a frontend.

## Setup

1. Create a PostgreSQL database named `knowledge_assistant`.
2. Make sure pgvector is installed for your PostgreSQL installation. The app enables the extension with `CREATE EXTENSION IF NOT EXISTS vector`, but it cannot install the extension files for you.
3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

4. Install packages:

   ```bash
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and update the PostgreSQL username/password and database URL. The application loads `.env` automatically.

6. Start Ollama and download the model:

   ```bash
   ollama pull llama3.2:3b
   ```

7. Start the API from the project root:

   ```bash
   uvicorn app.main:app --reload
   ```

8. Open the interactive API docs at `http://127.0.0.1:8000/docs`.

## Use the API

### Upload a PDF

Use `POST /documents/upload` and select a PDF file in the Swagger UI. The application extracts text page by page, chunks it, generates 384-dimensional embeddings, and stores the chunks.

### Ask a question

Use `POST /ask` with:

```json
{
  "question": "What is the leave application procedure?"
}
```

The response contains an answer and the retrieved source filenames/page numbers.

## Important notes

- The embedding model is downloaded the first time it is used; internet access may be needed for that initial download.
- `sentence-transformers/all-MiniLM-L6-v2` produces 384-dimensional vectors. The database column must use the same dimension.
- This simple version uses character-based chunk sizes for readability, not token-based chunking.
- Scanned/image-only PDFs need OCR; this project currently extracts selectable PDF text only.
- Re-uploading the same PDF inserts its chunks again. De-duplication and document deletion are intentionally left for a later learning step.
- Do not expose this development server publicly. It has no authentication or per-user access controls.

## Project structure

```text
app/
  config.py       # Environment-based settings
  database.py     # SQLAlchemy connection and pgvector table
  main.py         # FastAPI endpoints
  rag.py          # PDF chunking, embeddings, retrieval, LLM call
sql/
  schema.sql      # Equivalent SQL table definition
```
