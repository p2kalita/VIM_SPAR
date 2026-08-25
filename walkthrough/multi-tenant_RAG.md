# RAG Integration — Walkthrough

## What Was Done

The RAG system from the `RAG/` folder has been fully integrated into the Flask app. Here's what was created/modified:

---

## New Files

| File | Purpose |
|---|---|
| [`vim/rag/__init__.py`](file:///d:/Vendor-Invoice-Management-24JULY/vim/rag/__init__.py) | Package marker |
| [`vim/rag/store.py`](file:///d:/Vendor-Invoice-Management-24JULY/vim/rag/store.py) | ChromaDB vector store — ingest, retrieve, get stats |
| [`vim/rag/query_crew.py`](file:///d:/Vendor-Invoice-Management-24JULY/vim/rag/query_crew.py) | CrewAI synthesis agent (sync, Flask-compatible) |
| [`templates/vim_rag_assistant.html`](file:///d:/Vendor-Invoice-Management-24JULY/templates/vim_rag_assistant.html) | AI Assistant landing page (vendor selector + tabs) |
| [`templates/vim_rag_ingest_results.html`](file:///d:/Vendor-Invoice-Management-24JULY/templates/vim_rag_ingest_results.html) | Ingest success/error results page |
| [`templates/vim_rag_query_results.html`](file:///d:/Vendor-Invoice-Management-24JULY/templates/vim_rag_query_results.html) | CrewAI answer + raw ChromaDB chunks page |

## Modified Files

| File | Change |
|---|---|
| [`vim/vim_controller.py`](file:///d:/Vendor-Invoice-Management-24JULY/vim/vim_controller.py) | Added 3 new admin routes (see below) |
| [`requirements.txt`](file:///d:/Vendor-Invoice-Management-24JULY/requirements.txt) | Added RAG dependencies |

---

## New Flask Routes

| Route | Method | Purpose |
|---|---|---|
| `/admin/ai_assistant` | GET | Landing page — vendor selector, stats, ingest/query tabs |
| `/admin/rag_ingest` | POST | Upload PDF/TXT → ChromaDB for selected vendor |
| `/admin/rag_query` | POST | Natural language question → CrewAI → synthesized answer |

All routes are protected by `@admin_required`.

---

## Architecture

```
Admin Browser
    │
    ▼
Flask /admin/ai_assistant  (vendor selector)
    │
    ├── POST /admin/rag_ingest
    │       │
    │       └── vim/rag/store.py::ingest_invoice()
    │               → chunks text → ChromaDB (chroma_db/)
    │
    └── POST /admin/rag_query
            │
            ├── vim/rag/store.py::retrieve_chunks()
            │       → semantic search in ChromaDB (tenant-isolated)
            │
            └── vim/rag/query_crew.py::QueryCrew.run()
                    → CrewAI Agent (Gemini 2.5-flash)
                    → grounded synthesized answer
```

---

## How to Use

1. **Start the app:** `python app.py`
2. **Log in as admin** → click **🧠 AI Assistant (RAG)** on the dashboard
3. **Select a vendor** from the dropdown (maps to ChromaDB `tenant_id`)
4. **Ingest tab:** Upload PDF/TXT invoices → they get chunked into ChromaDB
5. **Query tab:** Ask a natural language question → get a CrewAI-synthesized answer with cited invoice numbers

---

## Verification Results

- ✅ All RAG packages present (`chromadb`, `crewai`, `sentence-transformers`, etc.)
- ✅ `vim.rag.store` imports cleanly
- ✅ `vim.rag.query_crew` imports cleanly

> [!IMPORTANT]
> The `.env` already has `GEMINI_API_KEY` set. The `chroma_db/` folder will be auto-created in the project root on first ingest.

> [!NOTE]
> The existing `RAG/` folder is **not deleted** — it's left as-is since it's the original standalone FastAPI app. The Flask app now uses `vim/rag/` instead.
