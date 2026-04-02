-- Enable ltree extension for materialized path hierarchy queries
-- This file is mounted into PostgreSQL's init directory and runs
-- automatically on first database creation.
CREATE EXTENSION IF NOT EXISTS ltree;
