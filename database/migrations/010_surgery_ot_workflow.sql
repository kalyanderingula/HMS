BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_surgery_request_schedule
    ON surgery.surgery_scheduling(surgery_request_id);
CREATE INDEX IF NOT EXISTS idx_surgery_room_schedule
    ON surgery.surgery_scheduling(ot_room_number, scheduled_start, scheduled_end);

ALTER TABLE surgery.surgery_requests
    ADD COLUMN IF NOT EXISTS encounter_id UUID,
    ADD COLUMN IF NOT EXISTS admission_id UUID,
    ADD COLUMN IF NOT EXISTS estimated_charge NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE surgery.surgery_scheduling
    ADD COLUMN IF NOT EXISTS actual_start TIMESTAMP,
    ADD COLUMN IF NOT EXISTS actual_end TIMESTAMP,
    ADD COLUMN IF NOT EXISTS anesthesia_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS complications TEXT,
    ADD COLUMN IF NOT EXISTS completed_by UUID;

CREATE TABLE IF NOT EXISTS surgery.ot_preoperative_checklists (
    checklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    surgery_request_id UUID NOT NULL UNIQUE REFERENCES surgery.surgery_requests(surgery_request_id),
    consent_verified BOOLEAN NOT NULL,
    identity_verified BOOLEAN NOT NULL,
    surgical_site_verified BOOLEAN NOT NULL,
    allergies_reviewed BOOLEAN NOT NULL,
    investigations_reviewed BOOLEAN NOT NULL,
    fasting_confirmed BOOLEAN NOT NULL,
    anesthesia_cleared BOOLEAN NOT NULL,
    asa_classification VARCHAR(20),
    notes TEXT,
    completed_by UUID,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS surgery.ot_recovery_records (
    recovery_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    surgery_schedule_id UUID NOT NULL UNIQUE REFERENCES surgery.surgery_scheduling(surgery_schedule_id),
    recovery_status VARCHAR(40) NOT NULL,
    pain_score INT NOT NULL CHECK (pain_score BETWEEN 0 AND 10),
    observations TEXT NOT NULL,
    disposition VARCHAR(40) NOT NULL,
    recorded_by UUID,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS surgery.ot_consumables (
    consumable_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    surgery_schedule_id UUID NOT NULL REFERENCES surgery.surgery_scheduling(surgery_schedule_id),
    item_name VARCHAR(255) NOT NULL,
    quantity NUMERIC(12,2) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14,2) NOT NULL CHECK (unit_price >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
