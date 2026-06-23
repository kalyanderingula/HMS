-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 7: BILLING & FINANCIAL MANAGEMENT
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS billing;
SET search_path TO billing, public;

-- =========================================================
-- MASTER TABLES
-- =========================================================

CREATE TABLE billing_statuses (
    billing_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Draft
-- Pending
-- Partially Paid
-- Paid
-- Cancelled
-- Refunded


CREATE TABLE payment_methods (
    payment_method_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    method_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Cash
-- Credit Card
-- Debit Card
-- UPI
-- Net Banking
-- Insurance


CREATE TABLE invoice_types (
    invoice_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- OPD
-- IPD
-- Pharmacy
-- Laboratory
-- Radiology


CREATE TABLE tax_types (
    tax_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tax_name VARCHAR(100),

    tax_percentage NUMERIC(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- GST 5%
-- GST 12%
-- GST 18%


CREATE TABLE discount_types (
    discount_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    discount_name VARCHAR(100),

    discount_percentage NUMERIC(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- BILLING ACCOUNTS
-- =========================================================

CREATE TABLE billing_accounts (
    billing_account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    account_number VARCHAR(100) UNIQUE NOT NULL,

    account_status VARCHAR(100),

    total_due NUMERIC(14,2) DEFAULT 0,

    total_paid NUMERIC(14,2) DEFAULT 0,

    insurance_provider VARCHAR(255),

    insurance_policy_number VARCHAR(255),

    credit_limit NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- patient_id references patients(patient_id)


-- =========================================================
-- INVOICES
-- =========================================================

CREATE TABLE invoices (
    invoice_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    invoice_number VARCHAR(100) UNIQUE NOT NULL,

    billing_account_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    admission_id UUID,

    appointment_id UUID,

    encounter_id UUID,

    invoice_type_id UUID,

    billing_status_id UUID,

    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    due_date DATE,

    subtotal_amount NUMERIC(14,2),

    tax_amount NUMERIC(14,2),

    discount_amount NUMERIC(14,2),

    total_amount NUMERIC(14,2),

    paid_amount NUMERIC(14,2) DEFAULT 0,

    balance_amount NUMERIC(14,2),

    notes TEXT,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (billing_account_id)
        REFERENCES billing_accounts(billing_account_id),

    FOREIGN KEY (invoice_type_id)
        REFERENCES invoice_types(invoice_type_id),

    FOREIGN KEY (billing_status_id)
        REFERENCES billing_statuses(billing_status_id)
);

-- patient_id references patients(patient_id)
-- admission_id references admissions(admission_id)
-- appointment_id references appointments(appointment_id)
-- encounter_id references patient_encounters(encounter_id)


-- =========================================================
-- INVOICE ITEMS
-- =========================================================

CREATE TABLE invoice_items (
    invoice_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID NOT NULL,

    item_type VARCHAR(100),

    item_reference_id UUID,

    item_name VARCHAR(255),

    quantity NUMERIC(12,2),

    unit_price NUMERIC(14,2),

    tax_type_id UUID,

    discount_type_id UUID,

    discount_amount NUMERIC(14,2),

    tax_amount NUMERIC(14,2),

    line_total NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id)
        ON DELETE CASCADE,

    FOREIGN KEY (tax_type_id)
        REFERENCES tax_types(tax_type_id),

    FOREIGN KEY (discount_type_id)
        REFERENCES discount_types(discount_type_id)
);

-- =========================================================
-- PAYMENTS
-- =========================================================

CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    payment_method_id UUID,

    payment_reference VARCHAR(255),

    transaction_id VARCHAR(255),

    payment_amount NUMERIC(14,2),

    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    payment_status VARCHAR(100),

    received_by UUID,

    notes TEXT,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id)
        ON DELETE CASCADE,

    FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(payment_method_id)
);

-- =========================================================
-- PAYMENT ALLOCATIONS
-- =========================================================

CREATE TABLE payment_allocations (
    payment_allocation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payment_id UUID NOT NULL,

    invoice_item_id UUID NOT NULL,

    allocated_amount NUMERIC(14,2),

    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id)
        ON DELETE CASCADE,

    FOREIGN KEY (invoice_item_id)
        REFERENCES invoice_items(invoice_item_id)
        ON DELETE CASCADE
);

-- =========================================================
-- INSURANCE CLAIMS
-- =========================================================

CREATE TABLE insurance_claims (
    insurance_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    insurance_provider VARCHAR(255),

    policy_number VARCHAR(255),

    claim_number VARCHAR(255),

    claim_amount NUMERIC(14,2),

    approved_amount NUMERIC(14,2),

    rejected_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    submitted_at TIMESTAMP,

    approved_at TIMESTAMP,

    rejection_reason TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id)
        ON DELETE CASCADE
);

-- =========================================================
-- REFUNDS
-- =========================================================

CREATE TABLE refunds (
    refund_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payment_id UUID NOT NULL,

    refund_reference VARCHAR(255),

    refund_amount NUMERIC(14,2),

    refund_reason TEXT,

    refund_status VARCHAR(100),

    refunded_by UUID,

    refunded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- CREDIT NOTES
-- =========================================================

CREATE TABLE credit_notes (
    credit_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID NOT NULL,

    credit_note_number VARCHAR(100) UNIQUE NOT NULL,

    credit_amount NUMERIC(14,2),

    reason TEXT,

    issued_by UUID,

    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEBIT NOTES
-- =========================================================

CREATE TABLE debit_notes (
    debit_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID NOT NULL,

    debit_note_number VARCHAR(100) UNIQUE NOT NULL,

    debit_amount NUMERIC(14,2),

    reason TEXT,

    issued_by UUID,

    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id)
        ON DELETE CASCADE
);

-- =========================================================
-- BILLING DOCUMENTS
-- =========================================================

CREATE TABLE billing_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID NOT NULL,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_by UUID,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id)
        ON DELETE CASCADE
);

-- =========================================================
-- REVENUE CENTERS
-- =========================================================

CREATE TABLE revenue_centers (
    revenue_center_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID,

    revenue_center_code VARCHAR(100) UNIQUE NOT NULL,

    revenue_center_name VARCHAR(255),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- department_id references departments(department_id)


-- =========================================================
-- FINANCIAL TRANSACTIONS
-- =========================================================

CREATE TABLE financial_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID,

    payment_id UUID,

    revenue_center_id UUID,

    transaction_type VARCHAR(100),

    debit_amount NUMERIC(14,2),

    credit_amount NUMERIC(14,2),

    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    narration TEXT,

    created_by UUID,

    FOREIGN KEY (invoice_id)
        REFERENCES invoices(invoice_id),

    FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id),

    FOREIGN KEY (revenue_center_id)
        REFERENCES revenue_centers(revenue_center_id)
);

-- =========================================================
-- BILLING AUDIT LOGS
-- =========================================================

CREATE TABLE billing_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID,

    payment_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT
);

-- =========================================================
-- BILLING CHANGE HISTORY
-- =========================================================

CREATE TABLE billing_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    invoice_id UUID,

    changed_field VARCHAR(255),

    old_value TEXT,

    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_billing_accounts_patient
ON billing_accounts(patient_id);

CREATE INDEX idx_invoices_patient
ON invoices(patient_id);

CREATE INDEX idx_invoices_admission
ON invoices(admission_id);

CREATE INDEX idx_invoices_appointment
ON invoices(appointment_id);

CREATE INDEX idx_invoice_items_invoice
ON invoice_items(invoice_id);

CREATE INDEX idx_payments_invoice
ON payments(invoice_id);

CREATE INDEX idx_payment_allocations_payment
ON payment_allocations(payment_id);

CREATE INDEX idx_insurance_claims_invoice
ON insurance_claims(invoice_id);

CREATE INDEX idx_refunds_payment
ON refunds(payment_id);

CREATE INDEX idx_credit_notes_invoice
ON credit_notes(invoice_id);

CREATE INDEX idx_debit_notes_invoice
ON debit_notes(invoice_id);

CREATE INDEX idx_billing_documents_invoice
ON billing_documents(invoice_id);

CREATE INDEX idx_financial_transactions_invoice
ON financial_transactions(invoice_id);

-- =========================================================
-- HIGH-LEVEL RELATIONSHIP FLOW
-- =========================================================

/*

billing_accounts
│
└── invoices
      │
      ├── invoice_items
      ├── payments
      │      ├── refunds
      │      └── payment_allocations
      │
      ├── insurance_claims
      ├── credit_notes
      ├── debit_notes
      ├── billing_documents
      ├── financial_transactions
      ├── billing_audit_logs
      └── billing_change_history

revenue_centers
│
└── financial_transactions

*/

-- =========================================================
-- END OF BILLING & FINANCIAL MANAGEMENT SCHEMA
-- =========================================================