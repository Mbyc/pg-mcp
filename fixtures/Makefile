SHELL := /bin/bash

DB_SMALL := pgmcp_small
DB_MEDIUM := pgmcp_medium
DB_LARGE := pgmcp_large

SMALL_SQL := ./small/setup.sql
MEDIUM_SQL := ./medium/setup.sql
LARGE_SQL := ./large/setup.sql

.PHONY: help setup-test-db setup-small setup-medium setup-large drop-small drop-medium drop-large drop-all

help:
	@echo "Targets:"
	@echo "  setup-test-db   - rebuild all (small/medium/large)"
	@echo "  setup-small     - rebuild $(DB_SMALL)"
	@echo "  setup-medium    - rebuild $(DB_MEDIUM)"
	@echo "  setup-large     - rebuild $(DB_LARGE)"
	@echo "Environment: PGHOST PGPORT PGUSER PGPASSWORD (optional PGDATABASE)"

setup-test-db: setup-small setup-medium setup-large

setup-small:
	@echo "Rebuilding $(DB_SMALL)..."
	-dropdb --if-exists $(DB_SMALL)
	createdb $(DB_SMALL)
	psql -v ON_ERROR_STOP=1 -d $(DB_SMALL) -f $(SMALL_SQL)

setup-medium:
	@echo "Rebuilding $(DB_MEDIUM)..."
	-dropdb --if-exists $(DB_MEDIUM)
	createdb $(DB_MEDIUM)
	psql -v ON_ERROR_STOP=1 -d $(DB_MEDIUM) -f $(MEDIUM_SQL)

setup-large:
	@echo "Rebuilding $(DB_LARGE)..."
	-dropdb --if-exists $(DB_LARGE)
	createdb $(DB_LARGE)
	psql -v ON_ERROR_STOP=1 -d $(DB_LARGE) -f $(LARGE_SQL)

drop-small:
	-dropdb --if-exists $(DB_SMALL)

drop-medium:
	-dropdb --if-exists $(DB_MEDIUM)

drop-large:
	-dropdb --if-exists $(DB_LARGE)

drop-all: drop-small drop-medium drop-large
