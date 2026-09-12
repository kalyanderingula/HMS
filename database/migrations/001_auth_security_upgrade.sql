ALTER TABLE security.users ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0;
ALTER TABLE security.users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;

ALTER TABLE security.user_sessions ADD COLUMN IF NOT EXISTS refresh_token_hash TEXT;
ALTER TABLE security.user_sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;
ALTER TABLE security.user_sessions ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP;
ALTER TABLE security.user_sessions ADD COLUMN IF NOT EXISTS user_agent TEXT;
ALTER TABLE security.user_sessions ADD COLUMN IF NOT EXISTS ip_address VARCHAR(255);

CREATE TABLE IF NOT EXISTS security.password_reset_tokens (
    reset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES security.users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE security.multi_factor_authentication ADD COLUMN IF NOT EXISTS secret TEXT;
ALTER TABLE security.multi_factor_authentication ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;
CREATE UNIQUE INDEX IF NOT EXISTS uq_security_mfa_user ON security.multi_factor_authentication(user_id);
CREATE INDEX IF NOT EXISTS ix_security_reset_token_hash ON security.password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS ix_security_session_refresh_hash ON security.user_sessions(refresh_token_hash);
