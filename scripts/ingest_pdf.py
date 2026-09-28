from __future__ import annotations

import argparse
from dataclasses import replace

from dotenv import load_dotenv

from rag.bootstrap import build_rag_service, resolve_source_paths
from rag.config import Settings
from rag.pdf_ingest import parse_source
from rag.store import PgVectorStore


def approved_ingest_sources():
    """Return every manifest-approved PDF and Apple Pages source."""
    return resolve_source_paths()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Index all approved real_data sources into PostgreSQL + pgvector. "
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
    parser.add_argument(
        "--images-only",
        action="store_true",
        help=(
            "Refresh source-only PDF visuals without recomputing text embeddings. "
            "Requires the same PDF hashes to already exist in PostgreSQL."
        ),
    )
    args = parser.parse_args()
    if args.text_only and args.images_only:
        parser.error("--text-only and --images-only cannot be used together")

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

    approved = approved_ingest_sources()

    if args.images_only:
        store = PgVectorStore(
            settings.database_url,
            embedding_dim=settings.embedding_dim,
        )
        store.ensure_schema()
        visual_count = 0
        for pdf_path in approved:
            document = parse_source(
                pdf_path,
                extract_images=True,
                render_vector_pages=True,
                chunk_size=settings.chunk_chars,
                overlap=settings.chunk_overlap,
            )
            store.replace_images(document)
            visual_count += len(document.images)
            print(
                f"Refreshed visuals: {pdf_path.name} "
                f"images={len(document.images)}"
            )
        print(
            "RAG visual catalog ready. "
            f"sources={len(approved)}, store={store.mode}, "
            f"internal_visuals={visual_count}"
        )
        return

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
