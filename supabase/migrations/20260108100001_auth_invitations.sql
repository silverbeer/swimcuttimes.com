-- =============================================================================
-- INVITATIONS
-- Invite-only registration system with role-based invite permissions
-- =============================================================================

CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'expired', 'revoked');

CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who sent the invite
    inviter_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,

    -- Invite details
    email TEXT NOT NULL,
    role user_role NOT NULL,
    token TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),

    -- Status tracking
    status invitation_status NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),

    -- If accepted, link to the new user
    accepted_by UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,

    -- For team invites: which team is the user being invited to
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique pending invite per email
    CONSTRAINT unique_pending_invite UNIQUE (email, status)
        DEFERRABLE INITIALLY DEFERRED
);

-- Partial unique index for pending invites only
DROP INDEX IF EXISTS idx_invitations_pending_email;
CREATE UNIQUE INDEX idx_invitations_pending_email
    ON invitations(email)
    WHERE status = 'pending';

-- Index for token lookup (accept invite flow)
CREATE INDEX idx_invitations_token ON invitations(token) WHERE status = 'pending';

-- Index for listing invites by inviter
CREATE INDEX idx_invitations_inviter ON invitations(inviter_id, status);

-- =============================================================================
-- INVITE PERMISSION VALIDATION
-- Enforces: admin→coach/swimmer, coach→swimmer/fan, swimmer→fan
-- =============================================================================

CREATE OR REPLACE FUNCTION validate_invite_permission()
RETURNS TRIGGER AS $$
DECLARE
    inviter_role user_role;
BEGIN
    -- Get inviter's role (uses security definer function to bypass RLS)
    inviter_role := get_user_role(NEW.inviter_id);

    IF inviter_role IS NULL THEN
        RAISE EXCEPTION 'Inviter not found or deleted';
    END IF;

    -- Validate permission based on role hierarchy
    CASE inviter_role
        WHEN 'admin' THEN
            -- Admins can invite anyone
            NULL;
        WHEN 'coach' THEN
            IF NEW.role NOT IN ('swimmer', 'fan') THEN
                RAISE EXCEPTION 'Coaches can only invite swimmers and fans';
            END IF;
        WHEN 'swimmer' THEN
            IF NEW.role != 'fan' THEN
                RAISE EXCEPTION 'Swimmers can only invite fans';
            END IF;
        WHEN 'fan' THEN
            RAISE EXCEPTION 'Fans cannot send invitations';
    END CASE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_invite_permission
    BEFORE INSERT ON invitations
    FOR EACH ROW EXECUTE FUNCTION validate_invite_permission();

-- =============================================================================
-- AUTO-EXPIRE OLD INVITATIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION expire_old_invitations()
RETURNS void AS $$
BEGIN
    UPDATE invitations
    SET status = 'expired'
    WHERE status = 'pending' AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;

-- Users can view invites they sent
CREATE POLICY "Users can view own invitations"
    ON invitations FOR SELECT
    USING (inviter_id = auth.uid());

-- Admins can view all invitations
CREATE POLICY "Admins can view all invitations"
    ON invitations FOR SELECT
    USING (is_admin());

-- Users can create invites (permission checked by trigger)
CREATE POLICY "Users can create invitations"
    ON invitations FOR INSERT
    WITH CHECK (inviter_id = auth.uid());

-- Users can revoke their own pending invites
CREATE POLICY "Users can revoke own invitations"
    ON invitations FOR UPDATE
    USING (inviter_id = auth.uid() AND status = 'pending')
    WITH CHECK (status = 'revoked');

-- Admins can update any invitation
CREATE POLICY "Admins can update invitations"
    ON invitations FOR UPDATE
    USING (is_admin());

COMMENT ON TABLE invitations IS 'Invite-only registration with role-based permissions';
COMMENT ON COLUMN invitations.token IS 'Secret token sent to invitee for signup';
COMMENT ON COLUMN invitations.team_id IS 'Optional team association for the invite';
