from __future__ import annotations

import argparse
from dataclasses import replace

from dotenv import load_dotenv

from rag.bootstrap import build_rag_service, resolve_pdf_paths
from rag.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Index all approved real_data PDFs into PostgreSQL + pgvector. "
            "Internal PDF images/page renders are prepared by default."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate chunks/embeddings even if the same PDF hash already exists.",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Skip internal PDF image extraction/page rendering for this ingest.",
    )
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()

    if not settings.database_url:
        raise SystemExit(
            "DATABASE_URL is not set. Add it to .env before running this script."
        )

    if not args.text_only:
        settings = replace(
            settings,
            extract_images=True,
            render_vector_pages=True,
        )

    approved = resolve_pdf_paths()
    service = build_rag_service(
        settings,
        force_reindex=args.force,
        require_database=True,
    )
    print(
        "RAG index ready. "
        f"sources={len(approved)}, store={service.store_mode}, "
        f"model={settings.embedding_model}, dim={settings.embedding_dim}, "
        f"internal_visuals={'off' if args.text_only else 'on'}"
    )


if __name__ == "__main__":
    main()
