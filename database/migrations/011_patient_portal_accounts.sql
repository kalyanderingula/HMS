BEGIN;

ALTER TABLE security.users
    ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patient.patients(patient_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_security_user_patient
    ON security.users(patient_id) WHERE patient_id IS NOT NULL;
INSERT INTO security.roles(role_name) VALUES('patient') ON CONFLICT(role_name) DO NOTHING;

COMMIT;
