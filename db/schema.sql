CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS rag_documents (
    source_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dim INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag_document_chunks (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES rag_documents(source_id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, page_number, chunk_index)
);

CREATE INDEX IF NOT EXISTS rag_chunks_source_page_idx
    ON rag_document_chunks (source_id, page_number);

CREATE INDEX IF NOT EXISTS rag_chunks_content_trgm_idx
    ON rag_document_chunks USING gin (content gin_trgm_ops);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw_idx
    ON rag_document_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS rag_document_images (
    id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES rag_documents(source_id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    image_index INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    image_bytes BYTEA NOT NULL,
    width INTEGER,
    height INTEGER,
    sha256 TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, page_number, image_index)
);

CREATE INDEX IF NOT EXISTS rag_images_source_page_idx
    ON rag_document_images (source_id, page_number);

CREATE TABLE IF NOT EXISTS rag_user_profiles (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag_chat_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES rag_user_profiles(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE rag_chat_sessions
    ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES rag_user_profiles(user_id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS rag_chat_sessions_user_idx
    ON rag_chat_sessions (user_id, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS rag_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES rag_chat_sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS rag_chat_messages_session_idx
    ON rag_chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS rag_chat_messages_role_idx
    ON rag_chat_messages (role, created_at DESC);

CREATE TABLE IF NOT EXISTS rag_retrieval_logs (
    id BIGSERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    elapsed_ms DOUBLE PRECISION NOT NULL,
    top_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    hit_pages JSONB NOT NULL DEFAULT '[]'::jsonb,
    hit_scores JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_retrieval_logs_created_idx
    ON rag_retrieval_logs (created_at);

CREATE TABLE IF NOT EXISTS rag_answer_logs (
    id BIGSERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    retrieval_ms DOUBLE PRECISION NOT NULL,
    ttft_ms DOUBLE PRECISION NOT NULL,
    total_ms DOUBLE PRECISION NOT NULL,
    top_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    answered BOOLEAN NOT NULL,
    model_name TEXT NOT NULL,
    hit_pages JSONB NOT NULL DEFAULT '[]'::jsonb,
    answer_chars INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_answer_logs_created_idx
    ON rag_answer_logs (created_at);
