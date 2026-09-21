"""Read-only audit of diagnostic tables in the configured PostgreSQL database."""
import asyncio

from sqlalchemy import text

from app.config import engine


async def main():
    async with engine.connect() as connection:
        tables = (await connection.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('laboratory', 'radiology', 'diagnostics')
            ORDER BY table_schema, table_name
        """))).all()
        print("\n".join(f"{schema}.{table}" for schema, table in tables))
        columns = (await connection.execute(text("""
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema IN ('laboratory', 'radiology', 'diagnostics')
              AND table_name IN (
                'lab_tests', 'lab_test_parameters', 'lab_test_reference_ranges',
                'radiology_tests', 'imaging_measurements', 'diagnostic_tests',
                'diagnostic_parameters', 'parameter_reference_ranges'
              )
            ORDER BY table_schema, table_name, ordinal_position
        """))).all()
        print("--- COLUMNS ---")
        print("\n".join(".".join(map(str, row)) for row in columns))
        counts = (await connection.execute(text("""
            SELECT 'lab reference ranges', count(*) FROM laboratory.lab_test_reference_ranges
            UNION ALL SELECT 'lab interpretation rules', count(*) FROM laboratory.lab_parameter_interpretation_rules
            UNION ALL SELECT 'radiology observation definitions', count(*) FROM radiology.radiology_observation_definitions
            UNION ALL SELECT 'radiology report approvals', count(*) FROM radiology.radiology_report_approvals
        """))).all()
        print("--- MASTER DATA COUNTS ---")
        print("\n".join(f"{label}: {count}" for label, count in counts))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
