BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_refund_reference ON billing.refunds(refund_reference);
CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_claim_number ON billing.insurance_claims(claim_number);
CREATE TABLE IF NOT EXISTS billing.billing_action_audit (
  audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), invoice_id UUID REFERENCES billing.invoices(invoice_id),
  action VARCHAR(50) NOT NULL, amount NUMERIC(14,2), reason TEXT NOT NULL, performed_by UUID,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
