CREATE TABLE IF NOT EXISTS security.identity_links (
    identity_link_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES security.users(user_id) ON DELETE CASCADE,
    identity_type VARCHAR(50) NOT NULL CHECK (identity_type IN ('employee','patient','doctor')),
    identity_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_identity_link_user_type UNIQUE (user_id, identity_type),
    CONSTRAINT uq_identity_link_type_id UNIQUE (identity_type, identity_id)
);

INSERT INTO security.identity_links (user_id, identity_type, identity_id)
SELECT user_id, 'employee', employee_id FROM security.users WHERE employee_id IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO security.identity_links (user_id, identity_type, identity_id)
SELECT user_id, 'patient', patient_id FROM security.users WHERE patient_id IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO security.identity_links (user_id, identity_type, identity_id)
SELECT DISTINCT ON (u.user_id) u.user_id, 'doctor', d.doctor_id
FROM security.users u
JOIN doctor.doctors d ON
    (u.employee_id IS NOT NULL AND d.employee_id = u.employee_id)
    OR (u.employee_id IS NULL AND d.employee_id IS NULL AND lower(d.doctor_code) = lower(u.username))
ORDER BY u.user_id, d.created_at NULLS LAST, d.doctor_id
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS ix_identity_links_user ON security.identity_links(user_id);
