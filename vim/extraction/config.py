import os
from pathlib import Path

from dotenv import load_dotenv, dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / "..env"
load_dotenv(ENV_PATH, override=True)

LLAMA_CLOUD_API_KEY: str = (os.getenv("LLAMA_CLOUD_API_KEY") or "").strip()
GROQ_API_KEY: str = (os.getenv("GROQ_API_KEY") or "").strip()
GROQ_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
# GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") -----------> deprecated this week
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


RESULT_TYPE: str = os.getenv("RESULT_TYPE", "markdown")
NUM_WORKERS: int = int(os.getenv("NUM_WORKERS", "4"))

UPLOAD_DIR: Path = PROJECT_ROOT / os.getenv("UPLOAD_DIR", "uploads/invoices")
OUTPUT_DIR: Path = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "output")

PARSING_INSTRUCTION: str = """
You are processing scanned or digital business documents (invoices,
purchase orders, bills, etc.).

Extract the full text content, preserving layout and structure:
- Keep headers, labels, and their associated values together.
- Reproduce tables (e.g. line items, charges, usage) as markdown tables,
  preserving row/column structure.
- Preserve reading order (top to bottom, left to right).
- Do not summarize, omit, or paraphrase any visible text.
- Do not output JSON — output plain markdown/text only.
""".strip()

SUPPORTED_EXTENSIONS: list[str] = [
    ".pdf", ".docx", ".pptx", ".html",
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def _read_keys() -> tuple[str, str]:
    load_dotenv(ENV_PATH, override=True)
    file_values = dotenv_values(ENV_PATH)
    llama = (file_values.get("LLAMA_CLOUD_API_KEY") or os.getenv("LLAMA_CLOUD_API_KEY") or "").strip()
    groq = (file_values.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    return llama, groq


def load_keys_into_app(app) -> tuple[str, str]:
    """Load API keys from ..env into Flask app.config (single source of truth)."""
    llama, groq = _read_keys()
    app.config["LLAMA_CLOUD_API_KEY"] = llama
    app.config["GROQ_API_KEY"] = groq
    global LLAMA_CLOUD_API_KEY, GROQ_API_KEY
    LLAMA_CLOUD_API_KEY, GROQ_API_KEY = llama, groq
    return llama, groq


def validate(app=None):
    """Raise early if required config is missing."""
    global LLAMA_CLOUD_API_KEY, GROQ_API_KEY

    if app is not None:
        llama = (app.config.get("LLAMA_CLOUD_API_KEY") or "").strip()
        groq = (app.config.get("GROQ_API_KEY") or "").strip()
    else:
        try:
            from flask import has_app_context, current_app
            if has_app_context():
                llama = (current_app.config.get("LLAMA_CLOUD_API_KEY") or "").strip()
                groq = (current_app.config.get("GROQ_API_KEY") or "").strip()
            else:
                llama, groq = "", ""
        except Exception:
            llama, groq = "", ""

    if not llama or not groq:
        llama, groq = _read_keys()

    LLAMA_CLOUD_API_KEY, GROQ_API_KEY = llama, groq

    if app is not None:
        app.config["LLAMA_CLOUD_API_KEY"] = llama
        app.config["GROQ_API_KEY"] = groq

    if not LLAMA_CLOUD_API_KEY or LLAMA_CLOUD_API_KEY == "llx-your-api-key-here":
        raise EnvironmentError(
            "\n\nLLAMA_CLOUD_API_KEY is not set.\n"
            "   1. Copy ..env.example to ..env\n"
            "   2. Add your key from https://cloud.llamaindex.ai\n"
        )
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "\n\nGROQ_API_KEY is not set.\n"
            "   Get your free key from https://console.groq.com\n"
            "   Add it to ..env\n"
        )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
