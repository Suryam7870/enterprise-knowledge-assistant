import requests
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from app.config import EMBEDDING_MODEL, OLLAMA_URL, OLLAMA_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
from app.database import DocumentChunk, SessionLocal

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model

def split_text(text: str) -> list[str]:
    if CHUNK_SIZE <= 0 or CHUNK_OVERLAP < 0 or CHUNK_OVERLAP >= CHUNK_SIZE:
        raise ValueError("CHUNK_SIZE must be positive and CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks

def index_pdf(file_path: str, filename: str) -> int:
    reader = PdfReader(file_path)
    records = []
    model = get_embedding_model()
    with SessionLocal() as db:
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            for chunk in split_text(page_text):
                vector = model.encode(chunk, normalize_embeddings=True).tolist()
                records.append(DocumentChunk(filename=filename, page_number=page_number, content=chunk, embedding=vector))
        db.add_all(records)
        db.commit()
    return len(records)

def retrieve(question: str):
    query_vector = get_embedding_model().encode(question, normalize_embeddings=True).tolist()
    with SessionLocal() as db:
        statement = (
            select(DocumentChunk)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(TOP_K)
        )
        return db.scalars(statement).all()

def generate_answer(question: str, chunks) -> str:
    if not chunks:
        return "I couldn't find relevant information in the uploaded documents."
    context = "\n\n".join(
        f"Source: {chunk.filename}, page {chunk.page_number}\n{chunk.content}"
        for chunk in chunks
    )
    prompt = f"""Answer the question using only the context below. If the context does not contain the answer, say you do not have enough information. Cite sources using the filename and page number.\n\nContext:\n{context}\n\nQuestion: {question}\nAnswer:"""
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["response"].strip()
