-- migration.sql

-- Create the 'emails' table with the new schema for IMAP sync.
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    sender TEXT NOT NULL,
    last_synced TIMESTAMP DEFAULT NOW(),
    folder TEXT NOT NULL,
    has_attachment BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'pending'
);

-- Create the 'folder_sync' table to track per-folder last sync markers.
CREATE TABLE IF NOT EXISTS folder_sync (
    folder TEXT PRIMARY KEY,
    last_sync TIMESTAMP DEFAULT NOW()
);

-- Existing tables for other features of the app:

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