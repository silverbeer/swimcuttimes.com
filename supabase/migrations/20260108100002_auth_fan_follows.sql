-- =============================================================================
-- FAN FOLLOWS
-- Fans can follow swimmers (via invite or request)
-- =============================================================================

CREATE TYPE follow_status AS ENUM ('pending', 'approved', 'denied');

CREATE TABLE fan_follows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- The fan (must have role = 'fan')
    fan_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,

    -- The swimmer being followed (must have role = 'swimmer')
    swimmer_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,

    -- How this follow was initiated
    initiated_by UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    -- initiated_by = fan_id means fan requested
    -- initiated_by = swimmer_id means swimmer invited

    status follow_status NOT NULL DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,

    -- Unique constraint: one follow relationship per fan-swimmer pair
    UNIQUE (fan_id, swimmer_id)
);

-- Index for fan's followed swimmers
CREATE INDEX idx_fan_follows_fan ON fan_follows(fan_id, status);

-- Index for swimmer's followers
CREATE INDEX idx_fan_follows_swimmer ON fan_follows(swimmer_id, status);

-- Index for pending requests/invites
CREATE INDEX idx_fan_follows_pending ON fan_follows(status) WHERE status = 'pending';

-- =============================================================================
-- VALIDATION
-- =============================================================================

CREATE OR REPLACE FUNCTION validate_fan_follow()
RETURNS TRIGGER AS $$
DECLARE
    fan_role user_role;
    swimmer_role user_role;
BEGIN
    -- Verify fan has role 'fan'
    SELECT role INTO fan_role
    FROM user_profiles
    WHERE id = NEW.fan_id AND deleted_at IS NULL;

    IF fan_role IS NULL OR fan_role != 'fan' THEN
        RAISE EXCEPTION 'fan_id must reference a user with role fan';
    END IF;

    -- Verify swimmer has role 'swimmer'
    SELECT role INTO swimmer_role
    FROM user_profiles
    WHERE id = NEW.swimmer_id AND deleted_at IS NULL;

    IF swimmer_role IS NULL OR swimmer_role != 'swimmer' THEN
        RAISE EXCEPTION 'swimmer_id must reference a user with role swimmer';
    END IF;

    -- Verify initiated_by is either the fan or swimmer
    IF NEW.initiated_by NOT IN (NEW.fan_id, NEW.swimmer_id) THEN
        RAISE EXCEPTION 'initiated_by must be either the fan or swimmer';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_fan_follow
    BEFORE INSERT ON fan_follows
    FOR EACH ROW EXECUTE FUNCTION validate_fan_follow();

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE fan_follows ENABLE ROW LEVEL SECURITY;

-- Fans can see their own follow relationships
CREATE POLICY "Fans can view own follows"
    ON fan_follows FOR SELECT
    USING (fan_id = auth.uid());

-- Swimmers can see their followers
CREATE POLICY "Swimmers can view own followers"
    ON fan_follows FOR SELECT
    USING (swimmer_id = auth.uid());

-- Admins can see all
CREATE POLICY "Admins can view all follows"
    ON fan_follows FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE id = auth.uid() AND role = 'admin' AND deleted_at IS NULL
        )
    );

-- Fans can request to follow (creates pending record)
CREATE POLICY "Fans can request to follow"
    ON fan_follows FOR INSERT
    WITH CHECK (
        fan_id = auth.uid()
        AND initiated_by = auth.uid()
        AND status = 'pending'
    );

-- Swimmers can invite fans (creates pending record)
CREATE POLICY "Swimmers can invite fans"
    ON fan_follows FOR INSERT
    WITH CHECK (
        swimmer_id = auth.uid()
        AND initiated_by = auth.uid()
        AND status = 'pending'
    );

-- Swimmers can approve/deny follow requests
CREATE POLICY "Swimmers can respond to follow requests"
    ON fan_follows FOR UPDATE
    USING (
        swimmer_id = auth.uid()
        AND status = 'pending'
        AND initiated_by = fan_id  -- Only requests from fans, not own invites
    )
    WITH CHECK (status IN ('approved', 'denied'));

-- Fans can accept/deny swimmer invites
CREATE POLICY "Fans can respond to follow invites"
    ON fan_follows FOR UPDATE
    USING (
        fan_id = auth.uid()
        AND status = 'pending'
        AND initiated_by = swimmer_id  -- Only invites from swimmers
    )
    WITH CHECK (status IN ('approved', 'denied'));

-- Fans can unfollow (delete approved follows they initiated)
CREATE POLICY "Fans can unfollow"
    ON fan_follows FOR DELETE
    USING (fan_id = auth.uid() AND status = 'approved');

-- Swimmers can remove followers
CREATE POLICY "Swimmers can remove followers"
    ON fan_follows FOR DELETE
    USING (swimmer_id = auth.uid());

-- Admins can do anything
CREATE POLICY "Admins can manage all follows"
    ON fan_follows FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE id = auth.uid() AND role = 'admin' AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE fan_follows IS 'Fan-swimmer follow relationships with request/invite flow';
COMMENT ON COLUMN fan_follows.initiated_by IS 'Who initiated: fan_id=request, swimmer_id=invite';
COMMENT ON COLUMN fan_follows.status IS 'pending=awaiting response, approved=active follow, denied=rejected';
