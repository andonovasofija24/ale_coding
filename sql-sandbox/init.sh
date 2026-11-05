#!/bin/sh
# Runs once when the sql-sandbox PostgreSQL starts with an empty data directory (its data is in memory,
# so: on every start). Creates the two roles the code runner uses for PostgreSQL tasks:
#   runner_admin — creates one throwaway database per test and drops it afterwards (no superuser).
#                  When the runner starts it gives `student` a new random password, so student code in other
#                  languages can't log in to PostgreSQL with a guessed one.
#   student      — the role student SQL runs as: owns only its test database, nothing else, time-limited
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<EOSQL
CREATE ROLE runner_admin LOGIN PASSWORD '${PG_SANDBOX_ADMIN_PASSWORD}' CREATEDB CREATEROLE NOSUPERUSER;
CREATE ROLE student LOGIN PASSWORD '${PG_SANDBOX_STUDENT_PASSWORD}'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 20;
GRANT student TO runner_admin WITH ADMIN OPTION;
ALTER ROLE student SET statement_timeout = '4s';
ALTER ROLE student SET lock_timeout = '2s';
ALTER ROLE student SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE student SET temp_file_limit = '64MB';
ALTER ROLE student SET work_mem = '8MB';
REVOKE CONNECT, TEMPORARY ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE template1 FROM PUBLIC;
GRANT CONNECT ON DATABASE postgres TO runner_admin;
EOSQL
