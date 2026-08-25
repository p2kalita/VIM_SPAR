import os
import uuid
from functools import lru_cache
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "tenant_invoices")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-en-v1.5")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "3"))
TENANT_KEY = "tenant_id"
INVOICE_KEY = "invoice_number"


@lru_cache(maxsize=1)
def get_collection(name: str = CHROMA_COLLECTION_NAME) -> chromadb.Collection:
    """Initialize ChromaDB with built-in SentenceTransformer embeddings."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL_NAME)
    return client.get_or_create_collection(
        name=name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-level chunks."""
    text = text.strip()
    chunks, start = [], 0
    while start < len(text):
        chunk = text[start: start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - chunk_overlap
    return chunks


def ingest_invoice(tenant_id: str, invoice_number: str, text: str) -> int:
    """Chunk and index an invoice tagged with tenant metadata. Returns chunk count."""
    chunks = chunk_text(text)
    documents, metadatas, ids = [], [], []
    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        metadatas.append({TENANT_KEY: tenant_id, INVOICE_KEY: invoice_number, "chunk_index": i})
        ids.append(str(uuid.uuid5(uuid.NAMESPACE_OID, f"{tenant_id}::{invoice_number}::{i}")))

    get_collection().upsert(documents=documents, metadatas=metadatas, ids=ids)
    return len(chunks)


def retrieve_chunks(
    tenant_id: str,
    query: str,
    invoice_number: Optional[str] = None,
    top_k: int = TOP_K,
) -> list[dict]:
    """Retrieve top-k chunks strictly isolated by tenant_id."""
    where = (
        {"$and": [{TENANT_KEY: {"$eq": tenant_id}}, {INVOICE_KEY: {"$eq": invoice_number}}]}
        if invoice_number
        else {TENANT_KEY: {"$eq": tenant_id}}
    )

    result = get_collection().query(
        query_texts=[query],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    ids = (result.get("ids") or [[]])[0]

    return [
        {
            "text": doc,
            "tenant_id": (meta or {}).get(TENANT_KEY, ""),
            "invoice_number": (meta or {}).get(INVOICE_KEY, ""),
            "chunk_index": (meta or {}).get("chunk_index", -1),
            "distance": dist,
            "id": cid,
        }
        for doc, meta, dist, cid in zip(docs, metas, distances, ids)
    ]


def format_chunks_for_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a prompt-ready context string."""
    if not chunks:
        return "No relevant invoice content was found for this query."
    return "\n\n---\n\n".join(
        f"[Chunk {i} | Invoice: {c['invoice_number']} | Similarity: {1 - c['distance']:.3f}]\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )


def get_vendor_data(vendor_id: str) -> dict:
    """Return collection statistics and stored invoices for a vendor workspace."""
    collection = get_collection()
    all_metadata = collection.get(include=["metadatas"])["metadatas"] or []
    all_tenants = {m.get(TENANT_KEY) for m in all_metadata if m and m.get(TENANT_KEY)}

    vendor_metadata = [m for m in all_metadata if m and m.get(TENANT_KEY) == vendor_id]
    vendor_invoices = list({m.get(INVOICE_KEY) for m in vendor_metadata if m and m.get(INVOICE_KEY)})

    return {
        "chunk_count": len(vendor_metadata),
        "invoice_count": len(vendor_invoices),
        "invoices": sorted(vendor_invoices),
        "total_chunks": collection.count(),
        "tenant_count": len(all_tenants),
        "all_tenants": sorted(all_tenants),
    }
