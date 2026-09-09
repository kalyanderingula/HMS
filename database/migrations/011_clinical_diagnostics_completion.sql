BEGIN;

-- 1. Doctor Acknowledgement & Tracking for Laboratory Results
ALTER TABLE laboratory.lab_result_entries
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS acknowledgement_notes TEXT;

-- 2. Doctor Acknowledgement & Critical Flags for Radiology Reports
ALTER TABLE radiology.radiology_reports
    ADD COLUMN IF NOT EXISTS is_critical BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS critical_alert_details TEXT,
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS acknowledgement_notes TEXT;

-- 3. PACS Imaging Series & Key Images for Studies
CREATE TABLE IF NOT EXISTS radiology.imaging_study_images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id UUID NOT NULL REFERENCES radiology.imaging_studies(study_id) ON DELETE CASCADE,
    series_number INT NOT NULL DEFAULT 1,
    instance_number INT NOT NULL DEFAULT 1,
    image_url TEXT NOT NULL,
    slice_description VARCHAR(255),
    is_key_image BOOLEAN NOT NULL DEFAULT FALSE,
    modality_code VARCHAR(50),
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_imaging_study_images_study ON radiology.imaging_study_images(study_id);

-- 4. Notification read tracking
ALTER TABLE core.notifications
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMP;

COMMIT;
