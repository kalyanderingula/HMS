BEGIN;

CREATE TABLE IF NOT EXISTS intensive_care_unit.icu_discharge_requests (
    icu_discharge_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    icu_admission_id UUID NOT NULL REFERENCES intensive_care_unit.icu_admissions(icu_admission_id),
    requested_by UUID NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    proposed_condition VARCHAR(255) NOT NULL,
    proposed_summary TEXT NOT NULL,
    request_notes TEXT,
    request_status VARCHAR(50) NOT NULL DEFAULT 'Pending'
        CHECK (request_status IN ('Pending','Approved','Rejected','Cancelled')),
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_icu_discharge_request
    ON intensive_care_unit.icu_discharge_requests(icu_admission_id)
    WHERE request_status='Pending';
CREATE INDEX IF NOT EXISTS idx_icu_discharge_requests_status
    ON intensive_care_unit.icu_discharge_requests(request_status, requested_at DESC);

COMMIT;
