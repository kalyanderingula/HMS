# FOLDER RESTRUCTURE PLAN
# This maps the architecture diagram layers to a clean production folder structure

# PROPOSED STRUCTURE (based on architecture image):
#
# hospital-management-system/
# │
# ├── docker-compose.yml
# ├── .env
# ├── pyproject.toml
# ├── requirements.txt
# ├── README.md
# │
# ├── docs/                              ← ALL documentation
# │   ├── architecture/                  ← Architecture image + diagrams
# │   ├── database/                      ← Schema documentation (35 .txt files)
# │   ├── setup/                         ← Docker guide, timetable
# │   └── api/                           ← API docs (future)
# │
# ├── database/                          ← DATABASE LAYER
# │   ├── schemas/                       ← 34 SQL files (single source of truth)
# │   ├── migrations/                    ← Alembic migrations (future)
# │   └── seeds/                         ← Master data inserts (future)
# │
# ├── scripts/                           ← Deployment scripts
# │   └── init-db.sh
# │
# ├── src/                               ← ALL SOURCE CODE
# │   ├── api_gateway/                   ← API GATEWAY LAYER
# │   │   ├── middleware/
# │   │   └── routes/
# │   │
# │   ├── services/                      ← APPLICATION SERVICE LAYER
# │   │   ├── patient_service/
# │   │   ├── appointment_service/
# │   │   ├── clinical_service/
# │   │   ├── laboratory_service/
# │   │   ├── pharmacy_service/
# │   │   ├── billing_service/
# │   │   ├── hr_employee_service/
# │   │   ├── inventory_service/
# │   │   ├── notification_service/
# │   │   └── report_service/
# │   │
# │   ├── data_access/                   ← DATA ACCESS LAYER
# │   │   ├── orm/
# │   │   └── repositories/
# │   │
# │   ├── ai/                            ← AGENTIC AI LAYER
# │   │   ├── orchestrator/
# │   │   ├── rag_modules/
# │   │   ├── agents/
# │   │   ├── memory/
# │   │   ├── tools/
# │   │   └── knowledge_sources/
# │   │
# │   ├── security/                      ← SECURITY LAYER
# │   │   ├── authentication/
# │   │   ├── authorization/
# │   │   └── encryption/
# │   │
# │   └── integrations/                  ← INTEGRATION LAYER (external systems)
# │
# ├── frontend/                          ← PRESENTATION LAYER
# │   ├── web/
# │   ├── mobile/
# │   └── admin_dashboard/
# │
# ├── infrastructure/                    ← DEPLOYMENT ARCHITECTURE
# │   ├── kubernetes/
# │   ├── ci_cd/
# │   ├── monitoring/
# │   └── logging/
# │
# └── tests/                             ← TESTING
#     ├── unit/
#     ├── integration/
#     └── e2e/
