ALTER TABLE laboratory.lab_orders
    ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS booking_source VARCHAR(40) NOT NULL DEFAULT 'Doctor',
    ADD COLUMN IF NOT EXISTS referral_type VARCHAR(40) NOT NULL DEFAULT 'Doctor Referral',
    ADD COLUMN IF NOT EXISTS referral_doctor_name VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_lab_orders_scheduled_at
    ON laboratory.lab_orders(scheduled_at);

CREATE INDEX IF NOT EXISTS idx_lab_orders_patient_scheduled
    ON laboratory.lab_orders(patient_id, scheduled_at);
