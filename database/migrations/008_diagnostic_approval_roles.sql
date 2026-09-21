INSERT INTO security.roles(role_name) VALUES ('pathologist')
ON CONFLICT(role_name) DO NOTHING;

ALTER TABLE radiology.radiologists ADD COLUMN IF NOT EXISTS user_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS uq_radiologists_user_id
    ON radiology.radiologists(user_id) WHERE user_id IS NOT NULL;
