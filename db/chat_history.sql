CREATE TABLE IF NOT EXISTS browser_chat_owners (
    token_hash TEXT PRIMARY KEY CHECK (length(token_hash) = 64),
    display_name TEXT NOT NULL CHECK (length(display_name) <= 120)
);

CREATE TABLE IF NOT EXISTS browser_chat_exchanges (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
    owner_hash TEXT NOT NULL REFERENCES browser_chat_owners(token_hash),
    persona_id TEXT NOT NULL CHECK (persona_id IN ('nui','saimai','bam','bas','kaka','sabaitae')),
    exchange_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    assistant_metadata TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (owner_hash, persona_id, exchange_id)
);

CREATE INDEX IF NOT EXISTS browser_chat_exchange_order
    ON browser_chat_exchanges(owner_hash, persona_id, order_id);
