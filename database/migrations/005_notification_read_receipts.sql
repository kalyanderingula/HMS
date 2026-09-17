CREATE TABLE IF NOT EXISTS core.notification_read_receipts (
    notification_id UUID NOT NULL REFERENCES core.notifications(notification_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES security.users(user_id) ON DELETE CASCADE,
    read_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_read_receipts_user
    ON core.notification_read_receipts(user_id, read_at DESC);
