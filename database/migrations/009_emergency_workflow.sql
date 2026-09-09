BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_emergency_triage_arrival
    ON emergency.emergency_triage_assessments(emergency_arrival_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_emergency_registration_arrival
    ON emergency.emergency_registrations(emergency_arrival_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_emergency_encounter_registration
    ON emergency.emergency_encounters(emergency_registration_id);

ALTER TABLE emergency.emergency_encounters
    ADD COLUMN IF NOT EXISTS disposition VARCHAR(40),
    ADD COLUMN IF NOT EXISTS disposition_notes TEXT,
    ADD COLUMN IF NOT EXISTS disposition_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS disposition_by UUID,
    ADD COLUMN IF NOT EXISTS admission_id UUID;

CREATE TABLE IF NOT EXISTS emergency.emergency_clinical_notes (
    emergency_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    emergency_encounter_id UUID NOT NULL REFERENCES emergency.emergency_encounters(emergency_encounter_id),
    note_type VARCHAR(50) NOT NULL,
    note_text TEXT NOT NULL,
    recorded_by UUID,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_emergency_notes_encounter
    ON emergency.emergency_clinical_notes(emergency_encounter_id, recorded_at);

COMMIT;
