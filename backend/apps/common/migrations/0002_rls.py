"""Enable fail-closed row level security on all merchant-data tables.

The runtime role (inua_app) is not a table owner and cannot bypass RLS. The
tenant is supplied per transaction with:

    SELECT set_config('app.current_user_id', '<uuid>', true)

Policies resolve the owning user through businesses_business.owner_id. If the
setting is absent or empty, app_current_user_id() returns NULL and every
merchant-data policy denies access.
"""
from django.db import migrations

FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION app_current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.current_user_id', true), '')::uuid
$$;
"""

BUSINESS_POLICY = """
ALTER TABLE businesses_business ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses_business FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS business_tenant_isolation ON businesses_business;
CREATE POLICY business_tenant_isolation ON businesses_business
    FOR ALL
    USING (owner_id = app_current_user_id())
    WITH CHECK (owner_id = app_current_user_id());
"""

# Every table below carries business_id and inherits isolation from the
# business row. FOR ALL covers SELECT/INSERT/UPDATE/DELETE.
CHILD_TABLES = [
    "compliance_businesscompliance",
    "documents_document",
    "financials_fundingneed",
    "financials_loan",
    "financials_monthlyfinancial",
    "financials_transaction",
    "ingestion_pendingstatement",
    "ingestion_statement",
    "opportunities_opportunitymatch",
    "readiness_readinessassessment",
]

CHILD_POLICY = """
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON {table};
CREATE POLICY tenant_isolation ON {table}
    FOR ALL
    USING (
        business_id IN (
            SELECT id FROM businesses_business
            WHERE owner_id = app_current_user_id()
        )
    )
    WITH CHECK (
        business_id IN (
            SELECT id FROM businesses_business
            WHERE owner_id = app_current_user_id()
        )
    );
"""

AUDIT_POLICY = """
ALTER TABLE audit_auditlog ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_auditlog FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON audit_auditlog;
CREATE POLICY tenant_isolation ON audit_auditlog
    FOR ALL
    USING (
        actor_id = app_current_user_id()
        OR business_id IN (
            SELECT id FROM businesses_business
            WHERE owner_id = app_current_user_id()
        )
    )
    WITH CHECK (
        actor_id = app_current_user_id()
        OR business_id IN (
            SELECT id FROM businesses_business
            WHERE owner_id = app_current_user_id()
        )
    );
"""

GRANT_SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'inua_app') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA public TO inua_app';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO inua_app';
        EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO inua_app';
        EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE inua_migrator IN SCHEMA public '
                'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO inua_app';
        EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE inua_migrator IN SCHEMA public '
                'GRANT USAGE, SELECT ON SEQUENCES TO inua_app';
    END IF;
END $$;
"""

REVERSE_SQL = """
DROP POLICY IF EXISTS business_tenant_isolation ON businesses_business;
DROP POLICY IF EXISTS tenant_isolation ON audit_auditlog;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("audit", "0001_initial"),
        ("businesses", "0001_initial"),
        ("compliance", "0001_initial"),
        ("documents", "0001_initial"),
        ("financials", "0001_initial"),
        ("ingestion", "0001_initial"),
        ("opportunities", "0001_initial"),
        ("readiness", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FUNCTION_SQL, "DROP FUNCTION IF EXISTS app_current_user_id();"),
        migrations.RunSQL(BUSINESS_POLICY, REVERSE_SQL),
        *[
            migrations.RunSQL(
                CHILD_POLICY.format(table=table),
                f"DROP POLICY IF EXISTS tenant_isolation ON {table};",
            )
            for table in CHILD_TABLES
        ],
        migrations.RunSQL(AUDIT_POLICY, REVERSE_SQL),
        migrations.RunSQL(GRANT_SQL, migrations.RunSQL.noop),
    ]
