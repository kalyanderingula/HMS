BEGIN;

ALTER TABLE intensive_care_unit.critical_care_patients
    ADD CONSTRAINT fk_critical_care_patient
    FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE RESTRICT;

ALTER TABLE intensive_care_unit.icu_vital_signs
    ADD COLUMN IF NOT EXISTS recorded_by UUID;

ALTER TABLE intensive_care_unit.critical_lab_alerts
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP;

ALTER TABLE intensive_care_unit.device_alerts
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS uq_icu_active_bed
    ON intensive_care_unit.icu_admissions(icu_bed_id)
    WHERE admission_status = 'Active';

CREATE INDEX IF NOT EXISTS idx_icu_vitals_admission_time
    ON intensive_care_unit.icu_vital_signs(icu_admission_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_icu_rounds_admission_time
    ON intensive_care_unit.icu_rounds(icu_admission_id, rounded_at DESC);

INSERT INTO intensive_care_unit.icu_departments
    (department_code, department_name, description)
VALUES ('ICU', 'Intensive Care Unit', 'Critical-care and high-dependency services')
ON CONFLICT (department_code) DO NOTHING;

INSERT INTO intensive_care_unit.icu_units
    (icu_department_id, unit_code, unit_name, unit_type, floor_number)
SELECT icu_department_id, 'MICU-01', 'Medical ICU', 'Medical', '1'
FROM intensive_care_unit.icu_departments WHERE department_code = 'ICU'
ON CONFLICT (unit_code) DO NOTHING;

INSERT INTO intensive_care_unit.icu_units
    (icu_department_id, unit_code, unit_name, unit_type, floor_number)
SELECT icu_department_id, 'SICU-01', 'Surgical ICU', 'Surgical', '1'
FROM intensive_care_unit.icu_departments WHERE department_code = 'ICU'
ON CONFLICT (unit_code) DO NOTHING;

INSERT INTO intensive_care_unit.icu_beds
    (icu_unit_id, bed_number, bed_type, bed_status, ventilator_supported, isolation_supported)
SELECT u.icu_unit_id, concat(u.unit_code, '-B', n), 'Critical Care', 'Available', TRUE, n = 4
FROM intensive_care_unit.icu_units u CROSS JOIN generate_series(1, 4) n
WHERE u.unit_code IN ('MICU-01', 'SICU-01')
  AND NOT EXISTS (
      SELECT 1 FROM intensive_care_unit.icu_beds b
      WHERE b.icu_unit_id = u.icu_unit_id AND b.bed_number = concat(u.unit_code, '-B', n)
  );

INSERT INTO intensive_care_unit.icu_triage_levels
    (level_name, severity_rank, description)
SELECT v.level_name, v.severity_rank, v.description
FROM (VALUES
    ('Immediate', 1, 'Immediate life-support intervention required'),
    ('Critical', 2, 'Continuous invasive monitoring or organ support required'),
    ('High Dependency', 3, 'Close observation and enhanced nursing required')
) AS v(level_name, severity_rank, description)
WHERE NOT EXISTS (
    SELECT 1 FROM intensive_care_unit.icu_triage_levels t WHERE t.level_name = v.level_name
);

COMMIT;
