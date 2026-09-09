BEGIN;

ALTER TABLE electronic_medical_records.medication_records
    ADD COLUMN IF NOT EXISTS drug_id UUID REFERENCES pharmacy.drugs(drug_id),
    ADD COLUMN IF NOT EXISTS quantity_prescribed NUMERIC(14,2),
    ADD COLUMN IF NOT EXISTS medication_status VARCHAR(40) DEFAULT 'Draft';

ALTER TABLE pharmacy.prescription_items
    ADD COLUMN IF NOT EXISTS medication_record_id UUID REFERENCES electronic_medical_records.medication_records(medication_record_id),
    ADD COLUMN IF NOT EXISTS quantity_dispensed NUMERIC(14,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS item_status VARCHAR(40) NOT NULL DEFAULT 'Pending';

ALTER TABLE pharmacy.dispensing_records
    ADD COLUMN IF NOT EXISTS dispensing_reference VARCHAR(100);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pharmacy_prescription_encounter
    ON pharmacy.prescriptions(encounter_id) WHERE encounter_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_prescription_item_medication
    ON pharmacy.prescription_items(medication_record_id) WHERE medication_record_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_item_source
    ON billing.invoice_items(item_type, item_reference_id) WHERE item_reference_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS pharmacy.prescription_amendments (
    amendment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prescription_id UUID NOT NULL REFERENCES pharmacy.prescriptions(prescription_id),
    prescription_item_id UUID REFERENCES pharmacy.prescription_items(prescription_item_id),
    action VARCHAR(40) NOT NULL,
    reason TEXT NOT NULL,
    before_value JSONB,
    after_value JSONB,
    amended_by UUID,
    amended_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispensing_items_prescription_item
    ON pharmacy.dispensing_items(prescription_item_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dispensing_reference
    ON pharmacy.dispensing_records(dispensing_reference) WHERE dispensing_reference IS NOT NULL;

COMMIT;
