import io
import sys
from pathlib import Path
from typing import List, Optional

# UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader

from query_crew import QueryCrew
from store import get_vendor_data, ingest_invoice, retrieve_chunks

app = FastAPI(title="Multi-Tenant Agentic RAG Portal")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, vendor_id: Optional[str] = None):
    if not vendor_id or not vendor_id.strip():
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"vendor_id": None},
        )

    vendor_id = vendor_id.strip().lower().replace(" ", "_")
    data = get_vendor_data(vendor_id)
    all_tenants_display = ", ".join(f"<code>{t}</code>" for t in data["all_tenants"]) or "None"
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"vendor_id": vendor_id, "data": data, "all_tenants_display": all_tenants_display},
    )


@app.post("/ingest", response_class=HTMLResponse)
async def ingest_endpoint(
    request: Request,
    vendor_id: str = Form(...),
    invoice_number: Optional[str] = Form(""),
    raw_text: Optional[str] = Form(""),
    files: List[UploadFile] = File(None),
):
    results = []

    if files:
        for file in files:
            if not file.filename:
                continue
            stem = Path(file.filename).stem
            inv_num = invoice_number.strip() if invoice_number and invoice_number.strip() else stem
            content = await file.read()

            text = ""
            if file.filename.lower().endswith(".pdf"):
                try:
                    reader = PdfReader(io.BytesIO(content))
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                except Exception as e:
                    results.append(f"❌ <b>{file.filename}</b>: PDF Extraction Error ({e})")
                    continue
            elif file.filename.lower().endswith(".txt"):
                text = content.decode("utf-8", errors="replace")
            else:
                results.append(f"❌ <b>{file.filename}</b>: Unsupported file format.")
                continue

            if not text.strip():
                results.append(f"❌ <b>{file.filename}</b>: File was empty.")
                continue

            try:
                chunks = ingest_invoice(tenant_id=vendor_id, invoice_number=inv_num, text=text)
                results.append(
                    f"✅ <b>{file.filename}</b> (Invoice: <code>{inv_num}</code>) &rarr; Indexed <b>{chunks}</b> chunk(s) under <code>tenant_id='{vendor_id}'</code>"
                )
            except Exception as e:
                results.append(f"❌ <b>{file.filename}</b>: Ingestion Error ({e})")

    if raw_text and raw_text.strip():
        inv_num = invoice_number.strip() if invoice_number and invoice_number.strip() else "PASTED-INV"
        try:
            chunks = ingest_invoice(tenant_id=vendor_id, invoice_number=inv_num, text=raw_text.strip())
            results.append(
                f"✅ Pasted Text (Invoice: <code>{inv_num}</code>) &rarr; Indexed <b>{chunks}</b> chunk(s) under <code>tenant_id='{vendor_id}'</code>"
            )
        except Exception as e:
            results.append(f"❌ Pasted Text Error: {e}")

    if not results:
        results.append("No files or text were provided to ingest.")

    return templates.TemplateResponse(
        request=request,
        name="ingest_results.html",
        context={"vendor_id": vendor_id, "results": results},
    )


@app.post("/query", response_class=HTMLResponse)
async def query_endpoint(
    request: Request,
    vendor_id: str = Form(...),
    query: str = Form(...),
    invoice_filter: Optional[str] = Form(""),
):
    inv_filter = invoice_filter.strip() if invoice_filter and invoice_filter.strip() else None

    # Retrieve isolated chunks from ChromaDB
    raw_chunks = retrieve_chunks(tenant_id=vendor_id, query=query, invoice_number=inv_filter, top_k=3)
    for c in raw_chunks:
        dist = c.get("distance")
        c["score_str"] = f"{1 - dist:.3f}" if dist is not None else "N/A"

    # Synthesize grounded answer via CrewAI
    try:
        crew = QueryCrew()
        answer = await crew.run_async(tenant_id=vendor_id, query=query, invoice_number=inv_filter)
    except Exception as e:
        answer = f"Agent execution error: {e}"

    filter_display = inv_filter if inv_filter else "All Invoices"
    return templates.TemplateResponse(
        request=request,
        name="query_results.html",
        context={
            "vendor_id": vendor_id,
            "filter_display": filter_display,
            "query": query,
            "answer": answer,
            "raw_chunks": raw_chunks,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
