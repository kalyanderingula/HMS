BEGIN;

ALTER TABLE blood_bank.blood_component_types
    ADD COLUMN IF NOT EXISTS unit_price NUMERIC(14,2) NOT NULL DEFAULT 1000;

ALTER TABLE blood_bank.blood_transfusions
    ADD COLUMN IF NOT EXISTS adverse_reaction BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reaction_details TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_blood_crossmatch_request_unit
    ON blood_bank.cross_match_tests(blood_request_id, blood_unit_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_blood_transfusion_unit
    ON blood_bank.blood_transfusions(blood_unit_id);

COMMIT;
