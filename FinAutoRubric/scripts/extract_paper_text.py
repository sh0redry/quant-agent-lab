"""Extract per-page text from the local paper PDF for fact checking.

Usage: python scripts/extract_paper_text.py [--pdf PATH] [--out PATH]

Output goes to .cache/ by default, which is Git-ignored: the extracted text is a
local working copy, not a deliverable. Quotes used as evidence are copied into
docs/ together with the page number they came from.
"""
import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=str(ROOT / "2609.35744v1.pdf"))
    parser.add_argument("--out", default=str(ROOT / ".cache"))
    args = parser.parse_args()

    pdf = Path(args.pdf)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw = pdf.read_bytes()
    reader = PdfReader(str(pdf))
    pages = [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]

    parts = []
    for number, text in pages:
        parts.append("===== PAGE %d =====" % number)
        parts.append(text)
    (out / "paper-extracted.txt").write_text("\n\n".join(parts), encoding="utf-8")

    meta = {
        "pdf": pdf.name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "page_count": len(pages),
        "pdf_metadata": {k: str(v) for k, v in (reader.metadata or {}).items()},
    }
    (out / "paper-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
