-- Additive compatibility migration; existing records are preserved.
ALTER TABLE surgery.surgery_requests ADD COLUMN IF NOT EXISTS procedure_code VARCHAR(100);
ALTER TABLE pharmacy.dispensing_records ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patient.patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_invoices_patient_date ON billing.invoices(patient_id,invoice_date DESC);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_reference ON billing.payments(invoice_id,payment_reference);
CREATE INDEX IF NOT EXISTS idx_active_admissions_bed ON admission.admissions(bed_id) WHERE actual_discharge_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_active_admissions_patient ON admission.admissions(patient_id) WHERE actual_discharge_date IS NULL;
