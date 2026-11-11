-- Idempotent role bootstrap for CI or an existing Postgres instance.
-- Usage (as a superuser):
--   psql -v ON_ERROR_STOP=1 -d postgres -f backend/scripts/bootstrap_roles.sql
-- Then create the app database owned by inua_migrator:
--   createdb -O inua_migrator inua360
-- The passwords below are development defaults only. Override them in real
-- environments and in the connection environment variables.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'inua_migrator') THEN
    CREATE ROLE inua_migrator LOGIN CREATEDB CREATEROLE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'inua_app') THEN
    CREATE ROLE inua_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

ALTER ROLE inua_migrator WITH LOGIN CREATEDB CREATEROLE NOSUPERUSER NOBYPASSRLS;
ALTER ROLE inua_app WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
ALTER ROLE inua_migrator PASSWORD 'inua_migrator_dev_password';
ALTER ROLE inua_app PASSWORD 'inua_app_dev_password';
