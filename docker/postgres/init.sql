-- Bootstrap the two-role model used by Inua360.
-- inua_migrator owns the tables and runs migrations.
-- inua_app is the runtime role: no superuser, no BYPASSRLS, not a table owner.
-- Passwords come from docker-compose environment via psql variables.
-- For CI, run scripts/bootstrap_roles.sql with psql instead.

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

GRANT ALL PRIVILEGES ON DATABASE inua360 TO inua_migrator;
GRANT CONNECT ON DATABASE inua360 TO inua_app;
GRANT USAGE ON SCHEMA public TO inua_app;

-- The migrator must own the database and schema so it can create/alter tables.
\connect postgres
ALTER DATABASE inua360 OWNER TO inua_migrator;
\connect inua360
ALTER SCHEMA public OWNER TO inua_migrator;
GRANT ALL ON SCHEMA public TO inua_migrator;
