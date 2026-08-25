import base64
import io
import json
from pathlib import Path

from groq import Groq
from PIL import Image, ImageEnhance

from vim.extraction import config
from vim.extraction.parser.core import parse_single_file
from vim.extraction.schema import empty_record, SCHEMA_DESCRIPTION_FOR_PROMPT
from vim.extraction.validator import validate_record

_groq_client = None


def _get_groq_client():
    global _groq_client
    config.validate()
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client

_EXTRACTION_PROMPT = f"""
This is the content of a business invoice or bill. It may be presented to
you as an image, or as text/markdown that was already extracted from a
PDF, DOCX, PPTX, or HTML file.

Extract its data into EXACTLY this JSON schema — same keys every time,
regardless of vendor or source format:

{SCHEMA_DESCRIPTION_FOR_PROMPT}

Rules:
- Use the exact key names above. Do not rename, add, or remove header keys.
- If a header field is not present on the document, use null (not "unknown",
  not an empty string).
- Normalize all dates to "YYYY-MM-DD".
- Normalize all money values to plain numbers (no "$", no commas, no
  currency symbols). A credit/payment should be negative.
- "line_items" is for the itemized charge/usage table on the invoice.
- "extra_fields" is a flat object for everything else printed on the document.
- Do not invent or infer anything not visible on the document.
- Return ONLY the JSON object. No markdown fences, no explanation.
""".strip()


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return text.strip()


def _finalize(raw_content: str) -> dict:
    raw = _strip_fences(raw_content)
    result = json.loads(raw)
    base = empty_record()
    base.update(result)
    return base


def parse_image_direct(file_path: str) -> dict:
    try:
        img = Image.open(file_path)

        if hasattr(img, "n_frames") and img.n_frames > 1:
            img.seek(0)

        img = img.convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(1.8)

        w, h = img.size
        if w > 1600 or h > 1600:
            scale = min(1600 / w, 1600 / h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        response = _get_groq_client().chat.completions.create(
            model=config.GROQ_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    },
                    {
                        "type": "text",
                        "text": _EXTRACTION_PROMPT,
                    }
                ]
            }],
            temperature=0.1,
            max_tokens=2000,
        )

        return _finalize(response.choices[0].message.content)

    except Exception as e:
        record = empty_record()
        record["_extraction_error"] = str(e)
        return record


def parse_text_direct(raw_text: str, source_label: str = "") -> dict:
    try:
        if not raw_text.strip():
            raise ValueError("no text extracted from source document")

        response = _get_groq_client().chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    f"{_EXTRACTION_PROMPT}\n\n"
                    f"--- DOCUMENT TEXT ({source_label}) ---\n{raw_text}"
                ),
            }],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        return _finalize(response.choices[0].message.content)

    except Exception as e:
        record = empty_record()
        record["_extraction_error"] = str(e)
        return record


def _extract_via_text(file_path: str) -> dict:
    """LlamaParse → Groq text model. Works for PDFs, images, and other docs."""
    path = Path(file_path)
    try:
        docs = parse_single_file(str(path), verbose=False)
        raw_text = "\n\n".join(d.text or "" for d in docs)
    except Exception as e:
        record = empty_record()
        record["_extraction_error"] = str(e)
        return record

    record = parse_text_direct(raw_text, source_label=path.name)
    record["raw_text"] = raw_text
    return record


def extract_from_file(file_path: str) -> dict:
    """Run the full extraction + validation pipeline on a single file."""
    path = Path(file_path)
    ext = path.suffix.lower()

    # Try Groq Vision for images only when a vision model is configured and available.
    # Most Groq accounts only have text models — fall back to LlamaParse + text.
    if ext in config.IMAGE_EXTENSIONS and config.GROQ_VISION_MODEL:
        record = parse_image_direct(str(path))
        if not record.get("_extraction_error") and record.get("total_due") is not None:
            pass  # vision succeeded
        else:
            record = _extract_via_text(str(path))
    else:
        record = _extract_via_text(str(path))

    record, issues = validate_record(record)
    record["file_name"] = path.name
    record["file_path"] = str(path)
    if issues:
        record["_validation_issues"] = issues

    return record
