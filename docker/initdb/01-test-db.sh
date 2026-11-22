#!/bin/sh
# Creates the separate database the backend tests run against.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE \"${POSTGRES_DB}_test\""
