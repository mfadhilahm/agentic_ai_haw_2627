import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_FILE = PROJECT_ROOT / "organization" / "company.md"


def read_project_document() -> dict:
    """Liest die Firmenbeschreibung und zerlegt sie in Absätze."""
    try:
        text = ALLOWED_FILE.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return {
            "status": "error",
            "message": f"Datei konnte nicht gelesen werden: {type(error).__name__}",
            "chunks": [],
        }

    paragraphs = [
        section.strip()
        for section in re.split(r"(?m)(?=^## )", text)
        if section.strip()
    ]

    if not paragraphs:
        return {
            "status": "error",
            "message": "Die Datei ist leer.",
            "chunks": [],
        }

    return {
        "status": "success",
        "source": "organization/company.md",
        "chunk_count": len(paragraphs),
        "chunks": [
            {"chunk_id": number, "text": paragraph}
            for number, paragraph in enumerate(paragraphs, start=1)
        ],
    }


if __name__ == "__main__":
    result = read_project_document()
    print(json.dumps(result, ensure_ascii=False, indent=2))