BEGIN;

ALTER TABLE telemedicine.virtual_appointments
    ADD COLUMN IF NOT EXISTS chief_complaint TEXT,
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Scheduled',
    ADD COLUMN IF NOT EXISTS emr_encounter_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'virtual_appointments_emr_encounter_id_fkey'
    ) THEN
        ALTER TABLE telemedicine.virtual_appointments
            ADD CONSTRAINT virtual_appointments_emr_encounter_id_fkey
            FOREIGN KEY (emr_encounter_id)
            REFERENCES electronic_medical_records.patient_encounters(encounter_id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_encounters_patient_date
    ON electronic_medical_records.patient_encounters(patient_id, encounter_date DESC);
CREATE INDEX IF NOT EXISTS idx_vitals_patient_recorded
    ON electronic_medical_records.vital_signs(patient_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_diagnoses_patient
    ON electronic_medical_records.diagnoses(patient_id, diagnosed_at DESC);
CREATE INDEX IF NOT EXISTS idx_virtual_appointments_patient_date
    ON telemedicine.virtual_appointments(patient_id, appointment_datetime DESC);

COMMIT;
