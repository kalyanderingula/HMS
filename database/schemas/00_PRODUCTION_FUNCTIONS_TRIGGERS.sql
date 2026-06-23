-- ==========================================
-- PRODUCTION FUNCTIONS & TRIGGERS
-- Enterprise Hospital Management System
-- ==========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to key tables
DO $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        AND tablename IN (
            SELECT table_name FROM information_schema.columns
            WHERE column_name = 'updated_at'
            AND table_schema NOT IN ('pg_catalog', 'information_schema')
        )
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_updated_at BEFORE UPDATE ON %I.%I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            t.schemaname, t.tablename
        );
    END LOOP;
EXCEPTION WHEN OTHERS THEN
    NULL;
END;
$$;
