from pathlib import Path
from llama_parse import LlamaParse
from vim.extraction import config


def _make_parser(**overrides) -> LlamaParse:
    return LlamaParse(
        api_key=config.LLAMA_CLOUD_API_KEY,
        result_type=overrides.get("result_type", config.RESULT_TYPE),
        parsing_instruction=overrides.get("parsing_instruction", config.PARSING_INSTRUCTION),
        verbose=overrides.get("verbose", True),
        num_workers=overrides.get("num_workers", config.NUM_WORKERS),
    )


def parse_single_file(file_path: str, **overrides) -> list:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.resolve()}")
    if overrides.get("verbose", True):
        print(f"\nParsing: {path.name}")
    parser = _make_parser(**overrides)
    documents = parser.load_data(str(path))
    if overrides.get("verbose", True):
        print(f"Done — {len(documents)} document(s) parsed.")
    return documents
