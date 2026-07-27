#!/bin/bash
set -e

# ============================================================
# HMS Database Initialization Script
# Executes all SQL schema files in the correct dependency order
# ============================================================

echo "============================================"
echo "Starting HMS Database Initialization..."
echo "============================================"

SCHEMAS_DIR="/docker-entrypoint-initdb.d/schemas"

# Define execution order - shared master tables must come first
declare -a FILE_ORDER=(
    "SHARED_MASTER_TABLES.sql"
    "Security, IAM (Identity & Access Management) & Compliance Management System.sql"
    "Multi-Hospital  Multi-Tenant Management System.sql"
    "patient.sql"
    "doctor.sql"
    "department.sql"
    "appointment_management.sql"
    "Electronic_Medical_Records.sql"
    "ADMISSION_&_BED_MANAGEMENT.sql"
    "BILLING_&_FINANCIAL_MANAGEMENT.sql"
    "PHARMACY_MANAGEMENT_SYSTEM.sql"
    "Laboratory Information System.sql"
    "RADIOLOGY INFORMATION SYSTEM.sql"
    "EMERGENCY_&_TRAUMA_MANAGEMENT_SYSTEM.sql"
    "SURGERY_&_OT_MANAGEMENT_SYSTEM.sql"
    "ICU_&_CRITICAL_CARE_MANAGEMENT_SYSTEM.sql"
    "NURSING_MANAGEMENT_SYSTEM.sql"
    "INSURANCE & CLAIMS MANAGEMENT SYSTEM.sql"
    "INVENTORY & PROCUREMENT MANAGEMENT SYSTEM.sql"
    "HR & PAYROLL MANAGEMENT SYSTEM.sql"
    "AMBULANCE & TRANSPORT MANAGEMENT SYSTEM.sql"
    "BLOOD_BANK_MANAGEMENT.sql"
    "DIETETICS_NUTRITION_MANAGEMENT.sql"
    "Category_19_Telemedicine_Virtual_Care.sql"
    "Category_20_CRM_Patient_Engagement.sql"
    "QUEUE_MANAGEMENT_SYSTEM.sql"
    "HOUSEKEEPING_MANAGEMENT.sql"
    "VISITOR_MANAGEMENT.sql"
    "BIOMEDICAL_WASTE_MANAGEMENT.sql"
    "MORTUARY_MEDICOLEGAL_MANAGEMENT.sql"
    "REHABILITATION_PHYSIOTHERAPY_MANAGEMENT.sql"
    "Analytics & Business Intelligence (BI) Management System.sql"
    "AI & CLINICAL DECISION SUPPORT SYSTEM.sql"
)

echo "--------------------------------------------"
echo "Executing schema files in dependency order..."
echo "--------------------------------------------"

# Process files in the defined order
for file in "${FILE_ORDER[@]}"; do
    FILE_PATH="${SCHEMAS_DIR}/${file}"
    if [ -f "$FILE_PATH" ]; then
        echo "Executing: $file"
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$FILE_PATH"
        echo "  -> Completed: $file"
    else
        echo "  -> WARNING: $file not found at $FILE_PATH, skipping..."
    fi
done

# Execute any remaining SQL files not in the explicit order
echo "--------------------------------------------"
echo "Executing any remaining SQL files..."
echo "--------------------------------------------"
for file in "$SCHEMAS_DIR"/*.sql; do
    filename=$(basename "$file")
    # Skip if already executed (in the ordered list above)
    skip=false
    for ordered_file in "${FILE_ORDER[@]}"; do
        if [ "$filename" = "$ordered_file" ]; then
            skip=true
            break
        fi
    done
    if [ "$skip" = false ]; then
        echo "Executing: $filename"
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$file"
        echo "  -> Completed: $filename"
    fi
done

# Run production functions and triggers after all schemas
echo "--------------------------------------------"
echo "Setting up production functions & triggers..."
echo "--------------------------------------------"
FUNCTIONS_FILE="${SCHEMAS_DIR}/00_PRODUCTION_FUNCTIONS_TRIGGERS.sql"
if [ -f "$FUNCTIONS_FILE" ]; then
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$FUNCTIONS_FILE"
    echo "  -> Completed: Production functions & triggers"
fi

# Run migrations
echo "--------------------------------------------"
echo "Running database migrations..."
echo "--------------------------------------------"
MIGRATIONS_DIR="/docker-entrypoint-initdb.d/migrations"
if [ -d "$MIGRATIONS_DIR" ]; then
    for migration_file in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration_file" ]; then
            echo "Executing migration: $(basename "$migration_file")"
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration_file"
            echo "  -> Completed: $(basename "$migration_file")"
        fi
    done
fi

echo "============================================"
echo "HMS Database Initialization Complete!"
echo "============================================"

# Verify schemas were created
echo ""
echo "Created schemas:"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
ORDER BY schema_name;"

echo ""
echo "Table count per schema:"
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT schemaname, count(*) as table_count
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname
ORDER BY schemaname;"

