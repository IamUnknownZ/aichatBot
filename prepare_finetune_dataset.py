"""Export the approved real_data corpus to JSONL without inventing Q&A.

This project uses closed-source RAG. The exporter therefore copies only text that
exists in approved PDFs under real_data/. It does not generate synthetic answers
or add facts from model memory/external sources.
"""

from __future__ import annotations

import json

from pypdf import PdfReader

from rag.bootstrap import resolve_pdf_paths

OUTPUT_JSONL = "real_data_corpus.jsonl"


def generate_jsonl() -> None:
    pdf_paths = resolve_pdf_paths()
    rows = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as output:
        for pdf_path in pdf_paths:
            reader = PdfReader(pdf_path)
            for page_number, page in enumerate(reader.pages, start=1):
                content = (page.extract_text() or "").strip()
                if not content:
                    continue

                entry = {
                    "source_file": pdf_path.name,
                    "physical_page": page_number,
                    "content": content,
                    "source_only": True,
                }
                output.write(
                    json.dumps(entry, ensure_ascii=False) + "\n"
                )
                rows += 1

    print(
        "Exported approved real_data corpus only: "
        f"sources={len(pdf_paths)}, rows={rows}, output={OUTPUT_JSONL}"
    )


if __name__ == "__main__":
    generate_jsonl()
