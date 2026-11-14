BEGIN;

ALTER TABLE intensive_care_unit.icu_admissions
    ADD COLUMN IF NOT EXISTS referring_doctor_id UUID REFERENCES doctor.doctors(doctor_id),
    ADD COLUMN IF NOT EXISTS attending_doctor_id UUID REFERENCES doctor.doctors(doctor_id),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_by UUID,
    ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;

ALTER TABLE intensive_care_unit.icu_vital_signs
    ADD COLUMN IF NOT EXISTS amended_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS amended_by UUID,
    ADD COLUMN IF NOT EXISTS amendment_reason TEXT,
    ADD COLUMN IF NOT EXISTS voided_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS voided_by UUID,
    ADD COLUMN IF NOT EXISTS void_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_icu_admission_attending
    ON intensive_care_unit.icu_admissions(attending_doctor_id, admission_status);

COMMIT;
