BEGIN;

INSERT INTO security.roles(role_name)
VALUES ('icu_viewer'),('icu_nurse'),('icu_doctor'),('icu_coordinator')
ON CONFLICT(role_name) DO NOTHING;

COMMIT;
