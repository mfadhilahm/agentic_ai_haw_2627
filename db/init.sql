-- Common database baseline for the course.
-- Application-specific tables and the actual RAG schema are team work.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS work_items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
    assigned_role TEXT NOT NULL DEFAULT 'backend_api_engineer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
