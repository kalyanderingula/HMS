BEGIN;
ALTER TABLE nursing.medication_administration_logs
  ADD COLUMN IF NOT EXISTS patient_id UUID,
  ADD COLUMN IF NOT EXISTS prescription_item_id UUID,
  ADD COLUMN IF NOT EXISTS medicine_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS route VARCHAR(100),
  ADD COLUMN IF NOT EXISTS administration_status VARCHAR(40) NOT NULL DEFAULT 'Administered',
  ADD COLUMN IF NOT EXISTS exception_reason TEXT;
ALTER TABLE nursing.medication_administration_logs
  DROP CONSTRAINT IF EXISTS medication_administration_logs_administered_by_fkey;
CREATE UNIQUE INDEX IF NOT EXISTS uq_nursing_log_mar ON nursing.medication_administration_logs(mar_id) WHERE mar_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_nursing_mar_dose ON nursing.medication_administration_records(patient_id,prescription_item_id,scheduled_time);
COMMIT;
