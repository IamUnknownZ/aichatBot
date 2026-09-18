from __future__ import annotations

import argparse

from dotenv import load_dotenv

from rag.bootstrap import build_rag_service
from rag.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index the project PDF into PostgreSQL + pgvector."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate chunks/embeddings even if the same PDF hash already exists.",
    )
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()

    if not settings.database_url:
        raise SystemExit(
            "DATABASE_URL is not set. Add it to .env before running this script."
        )

    service = build_rag_service(settings, force_reindex=args.force)
    print(
        "RAG index ready. "
        f"store={service.store_mode}, model={settings.embedding_model}, "
        f"dim={settings.embedding_dim}"
    )


if __name__ == "__main__":
    main()
