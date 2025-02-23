-- Create the emails table if it doesn't exist
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    sender TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT NOW(),
    content TEXT,
    status TEXT DEFAULT 'pending'
);

-- Now add the last_synced column if it's not already there
ALTER TABLE emails ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP DEFAULT NOW();

-- Existing migrations for other tables
CREATE TABLE IF NOT EXISTS email_flows (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    json_config JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS email_statuses (
    id SERIAL PRIMARY KEY,
    email_id TEXT UNIQUE NOT NULL,
    flow_id INT REFERENCES email_flows(id),
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS saved_filters (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    json_config JSONB NOT NULL
);