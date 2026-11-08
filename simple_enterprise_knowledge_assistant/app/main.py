import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from app.database import initialize_database
from app.rag import index_pdf, retrieve, generate_answer

app = FastAPI(title="Simple Enterprise Knowledge Assistant", version="1.0.0")

@app.on_event("startup")
def startup():
    initialize_database()

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            temp.write(content)
            temp_path = temp.name
        count = index_pdf(temp_path, os.path.basename(file.filename))
        if count == 0:
            raise HTTPException(status_code=422, detail="No extractable text found in this PDF")
        return {"filename": file.filename, "chunks_indexed": count}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/ask")
def ask_question(request: AskRequest):
    try:
        chunks = retrieve(request.question)
        answer = generate_answer(request.question, chunks)
        sources = [{"filename": c.filename, "page_number": c.page_number} for c in chunks]
        return {"question": request.question, "answer": answer, "sources": sources}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question processing failed: {exc}") from exc
