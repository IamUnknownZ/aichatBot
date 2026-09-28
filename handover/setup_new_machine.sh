#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[1/6] Python"
"$PYTHON_BIN" --version

echo "[2/6] Create fresh venv"
if [ ! -d "venv" ]; then
  "$PYTHON_BIN" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "[3/6] Install dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[4/6] Check private environment"
if [ ! -f ".env" ]; then
  echo "ERROR: .env is missing."
  echo "Copy the private .env from the old machine before running production."
  exit 1
fi

python - <<'PY'
from dotenv import load_dotenv
load_dotenv(".env")
from rag.config import Settings
s = Settings.from_env()
print("GEMINI_API_KEY configured:", bool(s.gemini_api_key))
print("DATABASE_URL configured:", bool(s.database_url))
if not s.gemini_api_key or not s.database_url:
    raise SystemExit("Missing required environment values")
PY

echo "[5/6] Verify Supabase/pgvector"
python - <<'PY'
from dotenv import load_dotenv
load_dotenv(".env")
from rag.config import Settings
import psycopg

s = Settings.from_env()
with psycopg.connect(s.database_url, connect_timeout=10) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "select extname from pg_extension "
            "where extname in ('vector','pg_trgm') order by extname"
        )
        extensions = [row[0] for row in cur.fetchall()]
        print("extensions:", extensions)
        if "vector" not in extensions or "pg_trgm" not in extensions:
            raise SystemExit("Required PostgreSQL extensions are missing")

        cur.execute("select count(*) from rag_document_chunks")
        chunks = cur.fetchone()[0]
        cur.execute(
            "select count(*) from rag_document_chunks "
            "where embedding is not null"
        )
        vectors = cur.fetchone()[0]
        cur.execute("select count(*) from rag_document_images")
        images = cur.fetchone()[0]

        print("chunks:", chunks)
        print("vectors:", vectors)
        print("images:", images)
PY

echo "[6/6] Run tests"
python -m unittest discover -s tests -p 'test_*.py'

echo
echo "Setup OK."
echo "Run:"
echo "  source venv/bin/activate"
echo "  python -m streamlit run app.py"
