-- Migration: Change from UUIDs to short IDs
-- Short IDs are 12 characters, alphanumeric, URL-safe

-- =============================================================================
-- SHORT ID GENERATION FUNCTION
-- =============================================================================

-- Create a function to generate short IDs (nanoid-style)
-- Uses a-z, 0-9 (36 chars) for 12 characters = 4.7 x 10^18 combinations
CREATE OR REPLACE FUNCTION generate_short_id(length INT DEFAULT 12)
RETURNS TEXT AS $$
DECLARE
    chars TEXT := 'abcdefghijklmnopqrstuvwxyz0123456789';
    result TEXT := '';
    i INT;
BEGIN
    FOR i IN 1..length LOOP
        result := result || substr(chars, floor(random() * 36 + 1)::int, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql VOLATILE
SET search_path = '';

-- =============================================================================
-- DROP POLICIES THAT REFERENCE ID COLUMNS
-- These will be recreated after type changes
-- =============================================================================

-- Policies on swimmer_suits that reference swimmers.id
DROP POLICY IF EXISTS "Swimmers can update own suits" ON swimmer_suits;

-- Policies on fan_follows that reference swimmers.id or swimmer_id
DROP POLICY IF EXISTS "Swimmers can view own followers" ON fan_follows;
DROP POLICY IF EXISTS "Swimmers can respond to follow requests" ON fan_follows;
DROP POLICY IF EXISTS "Swimmers can invite fans" ON fan_follows;
DROP POLICY IF EXISTS "Swimmers can remove followers" ON fan_follows;
DROP POLICY IF EXISTS "Fans can respond to follow invites" ON fan_follows;
DROP POLICY IF EXISTS "Fans can request to follow" ON fan_follows;
DROP POLICY IF EXISTS "Fans can view own follows" ON fan_follows;
DROP POLICY IF EXISTS "Fans can unfollow" ON fan_follows;

-- =============================================================================
-- TEAMS TABLE
-- =============================================================================

-- Drop foreign key constraints that reference teams
ALTER TABLE swimmer_teams DROP CONSTRAINT IF EXISTS swimmer_teams_team_id_fkey;
ALTER TABLE swim_times DROP CONSTRAINT IF EXISTS swim_times_team_id_fkey;
ALTER TABLE invitations DROP CONSTRAINT IF EXISTS invitations_team_id_fkey;
-- Note: meets_teams table does not exist, removed reference

-- Change teams.id from UUID to TEXT
ALTER TABLE teams ALTER COLUMN id DROP DEFAULT;
ALTER TABLE teams ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE teams ALTER COLUMN id SET DEFAULT generate_short_id();

-- Update existing UUIDs to short IDs
UPDATE teams SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- SWIMMERS TABLE
-- =============================================================================

-- Drop foreign key constraints that reference swimmers
ALTER TABLE swimmer_teams DROP CONSTRAINT IF EXISTS swimmer_teams_swimmer_id_fkey;
ALTER TABLE swim_times DROP CONSTRAINT IF EXISTS swim_times_swimmer_id_fkey;
ALTER TABLE swimmer_suits DROP CONSTRAINT IF EXISTS swimmer_suits_swimmer_id_fkey;
ALTER TABLE fan_follows DROP CONSTRAINT IF EXISTS fan_follows_swimmer_id_fkey;
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_swimmer_id_fkey;

-- Change swimmers.id from UUID to TEXT
ALTER TABLE swimmers ALTER COLUMN id DROP DEFAULT;
ALTER TABLE swimmers ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE swimmers ALTER COLUMN id SET DEFAULT generate_short_id();

-- Keep user_id as UUID (references auth.users)

-- Update existing UUIDs to short IDs
UPDATE swimmers SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- EVENTS TABLE
-- =============================================================================

-- Drop foreign key constraints that reference events
ALTER TABLE time_standards DROP CONSTRAINT IF EXISTS time_standards_event_id_fkey;
ALTER TABLE swim_times DROP CONSTRAINT IF EXISTS swim_times_event_id_fkey;

-- Change events.id from UUID to TEXT
ALTER TABLE events ALTER COLUMN id DROP DEFAULT;
ALTER TABLE events ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE events ALTER COLUMN id SET DEFAULT generate_short_id();

-- Update existing UUIDs to short IDs
UPDATE events SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- MEETS TABLE
-- =============================================================================

-- Drop foreign key constraints that reference meets
ALTER TABLE swim_times DROP CONSTRAINT IF EXISTS swim_times_meet_id_fkey;
-- Note: meets_teams table does not exist, removed reference

-- Change meets.id from UUID to TEXT
ALTER TABLE meets ALTER COLUMN id DROP DEFAULT;
ALTER TABLE meets ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE meets ALTER COLUMN id SET DEFAULT generate_short_id();

-- Update existing UUIDs to short IDs
UPDATE meets SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- SWIMMER_TEAMS TABLE
-- =============================================================================

-- Change swimmer_teams.id from UUID to TEXT
ALTER TABLE swimmer_teams ALTER COLUMN id DROP DEFAULT;
ALTER TABLE swimmer_teams ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE swimmer_teams ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change foreign key columns
ALTER TABLE swimmer_teams ALTER COLUMN swimmer_id TYPE TEXT USING swimmer_id::TEXT;
ALTER TABLE swimmer_teams ALTER COLUMN team_id TYPE TEXT USING team_id::TEXT;

-- Update existing UUIDs to short IDs
UPDATE swimmer_teams SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- TIME_STANDARDS TABLE
-- =============================================================================

-- Change time_standards.id from UUID to TEXT
ALTER TABLE time_standards ALTER COLUMN id DROP DEFAULT;
ALTER TABLE time_standards ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE time_standards ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change foreign key columns
ALTER TABLE time_standards ALTER COLUMN event_id TYPE TEXT USING event_id::TEXT;

-- Update existing UUIDs to short IDs
UPDATE time_standards SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- SWIM_TIMES TABLE
-- =============================================================================

-- Drop foreign key constraints that reference swim_times
ALTER TABLE splits DROP CONSTRAINT IF EXISTS splits_swim_time_id_fkey;

-- Drop FK constraint on suit_id (references swimmer_suits which is not yet converted)
ALTER TABLE swim_times DROP CONSTRAINT IF EXISTS swim_times_suit_id_fkey;

-- Change swim_times.id from UUID to TEXT
ALTER TABLE swim_times ALTER COLUMN id DROP DEFAULT;
ALTER TABLE swim_times ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE swim_times ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change foreign key columns
ALTER TABLE swim_times ALTER COLUMN swimmer_id TYPE TEXT USING swimmer_id::TEXT;
ALTER TABLE swim_times ALTER COLUMN event_id TYPE TEXT USING event_id::TEXT;
ALTER TABLE swim_times ALTER COLUMN meet_id TYPE TEXT USING meet_id::TEXT;
ALTER TABLE swim_times ALTER COLUMN team_id TYPE TEXT USING team_id::TEXT;
ALTER TABLE swim_times ALTER COLUMN suit_id TYPE TEXT USING suit_id::TEXT;

-- Update existing UUIDs to short IDs
UPDATE swim_times SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- SPLITS TABLE
-- =============================================================================

-- Change splits.id from UUID to TEXT
ALTER TABLE splits ALTER COLUMN id DROP DEFAULT;
ALTER TABLE splits ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE splits ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change foreign key column
ALTER TABLE splits ALTER COLUMN swim_time_id TYPE TEXT USING swim_time_id::TEXT;

-- Update existing UUIDs to short IDs
UPDATE splits SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- SUIT_MODELS TABLE
-- =============================================================================

-- Drop foreign key constraints that reference suit_models
ALTER TABLE swimmer_suits DROP CONSTRAINT IF EXISTS swimmer_suits_suit_model_id_fkey;

-- Change suit_models.id from UUID to TEXT
ALTER TABLE suit_models ALTER COLUMN id DROP DEFAULT;
ALTER TABLE suit_models ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE suit_models ALTER COLUMN id SET DEFAULT generate_short_id();

-- Update existing UUIDs to short IDs
UPDATE suit_models SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- SWIMMER_SUITS TABLE
-- =============================================================================

-- Drop foreign key constraints that reference swimmer_suits
ALTER TABLE swim_times DROP CONSTRAINT IF EXISTS swim_times_suit_id_fkey;

-- Change swimmer_suits.id from UUID to TEXT
ALTER TABLE swimmer_suits ALTER COLUMN id DROP DEFAULT;
ALTER TABLE swimmer_suits ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE swimmer_suits ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change foreign key columns
ALTER TABLE swimmer_suits ALTER COLUMN swimmer_id TYPE TEXT USING swimmer_id::TEXT;
ALTER TABLE swimmer_suits ALTER COLUMN suit_model_id TYPE TEXT USING suit_model_id::TEXT;

-- Update existing UUIDs to short IDs
UPDATE swimmer_suits SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- USER_PROFILES TABLE
-- Note: user_profiles.id stays as UUID since it references auth.users(id) directly
-- Only change swimmer_id to TEXT (references swimmers)
-- =============================================================================

-- Drop foreign key constraint
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_swimmer_id_fkey;

-- Change swimmer_id from UUID to TEXT
ALTER TABLE user_profiles ALTER COLUMN swimmer_id TYPE TEXT USING swimmer_id::TEXT;

-- =============================================================================
-- INVITATIONS TABLE
-- =============================================================================

-- Drop foreign key constraint for team_id
ALTER TABLE invitations DROP CONSTRAINT IF EXISTS invitations_team_id_fkey;

-- Change invitations.id from UUID to TEXT
ALTER TABLE invitations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE invitations ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE invitations ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change team_id from UUID to TEXT
ALTER TABLE invitations ALTER COLUMN team_id TYPE TEXT USING team_id::TEXT;

-- Keep invited_by and accepted_by as UUID (references auth.users)

-- Update existing UUIDs to short IDs
UPDATE invitations SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- FAN_FOLLOWS TABLE
-- =============================================================================

-- Note: fan_follows_swimmer_id_fkey was already dropped earlier in this migration

-- Change fan_follows.id from UUID to TEXT
ALTER TABLE fan_follows ALTER COLUMN id DROP DEFAULT;
ALTER TABLE fan_follows ALTER COLUMN id TYPE TEXT USING id::TEXT;
ALTER TABLE fan_follows ALTER COLUMN id SET DEFAULT generate_short_id();

-- Change swimmer_id to TEXT
ALTER TABLE fan_follows ALTER COLUMN swimmer_id TYPE TEXT USING swimmer_id::TEXT;

-- Keep fan_id and initiated_by as UUID (references auth.users)

-- Update existing UUIDs to short IDs
UPDATE fan_follows SET id = generate_short_id() WHERE length(id) > 12;

-- =============================================================================
-- RE-ADD FOREIGN KEY CONSTRAINTS
-- =============================================================================

-- swimmer_teams
ALTER TABLE swimmer_teams
    ADD CONSTRAINT swimmer_teams_swimmer_id_fkey
    FOREIGN KEY (swimmer_id) REFERENCES swimmers(id) ON DELETE CASCADE;
ALTER TABLE swimmer_teams
    ADD CONSTRAINT swimmer_teams_team_id_fkey
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;

-- time_standards
ALTER TABLE time_standards
    ADD CONSTRAINT time_standards_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id);

-- swim_times
ALTER TABLE swim_times
    ADD CONSTRAINT swim_times_swimmer_id_fkey
    FOREIGN KEY (swimmer_id) REFERENCES swimmers(id) ON DELETE CASCADE;
ALTER TABLE swim_times
    ADD CONSTRAINT swim_times_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id);
ALTER TABLE swim_times
    ADD CONSTRAINT swim_times_meet_id_fkey
    FOREIGN KEY (meet_id) REFERENCES meets(id);
ALTER TABLE swim_times
    ADD CONSTRAINT swim_times_team_id_fkey
    FOREIGN KEY (team_id) REFERENCES teams(id);
ALTER TABLE swim_times
    ADD CONSTRAINT swim_times_suit_id_fkey
    FOREIGN KEY (suit_id) REFERENCES swimmer_suits(id);

-- splits
ALTER TABLE splits
    ADD CONSTRAINT splits_swim_time_id_fkey
    FOREIGN KEY (swim_time_id) REFERENCES swim_times(id) ON DELETE CASCADE;

-- swimmer_suits
ALTER TABLE swimmer_suits
    ADD CONSTRAINT swimmer_suits_swimmer_id_fkey
    FOREIGN KEY (swimmer_id) REFERENCES swimmers(id) ON DELETE CASCADE;
ALTER TABLE swimmer_suits
    ADD CONSTRAINT swimmer_suits_suit_model_id_fkey
    FOREIGN KEY (suit_model_id) REFERENCES suit_models(id);

-- fan_follows
ALTER TABLE fan_follows
    ADD CONSTRAINT fan_follows_swimmer_id_fkey
    FOREIGN KEY (swimmer_id) REFERENCES swimmers(id) ON DELETE CASCADE;

-- user_profiles
ALTER TABLE user_profiles
    ADD CONSTRAINT user_profiles_swimmer_id_fkey
    FOREIGN KEY (swimmer_id) REFERENCES swimmers(id) ON DELETE SET NULL;

-- invitations
ALTER TABLE invitations
    ADD CONSTRAINT invitations_team_id_fkey
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL;

-- =============================================================================
-- RE-ADD POLICIES (fixed for TEXT swimmer_id)
-- =============================================================================

-- Swimmer suits: Swimmers can update own suits
CREATE POLICY "Swimmers can update own suits"
    ON swimmer_suits FOR UPDATE
    USING (
        swimmer_id IN (
            SELECT id FROM swimmers WHERE user_id = auth.uid()
        )
    );

-- Fan follows: Swimmers can view own followers
-- Note: swimmer_id is now TEXT, use subquery to find swimmer by user_id
CREATE POLICY "Swimmers can view own followers"
    ON fan_follows FOR SELECT
    USING (
        swimmer_id IN (
            SELECT id FROM swimmers WHERE user_id = auth.uid()
        )
    );

-- Fan follows: Swimmers can respond to follow requests
CREATE POLICY "Swimmers can respond to follow requests"
    ON fan_follows FOR UPDATE
    USING (
        swimmer_id IN (SELECT id FROM swimmers WHERE user_id = auth.uid())
        AND status = 'pending'
        AND initiated_by = fan_id
    );

-- Fan follows: Swimmers can invite fans
CREATE POLICY "Swimmers can invite fans"
    ON fan_follows FOR INSERT
    WITH CHECK (
        swimmer_id IN (SELECT id FROM swimmers WHERE user_id = auth.uid())
        AND initiated_by = auth.uid()
        AND status = 'pending'
    );

-- Fan follows: Swimmers can remove followers
CREATE POLICY "Swimmers can remove followers"
    ON fan_follows FOR DELETE
    USING (
        swimmer_id IN (SELECT id FROM swimmers WHERE user_id = auth.uid())
    );

-- Fan follows: Fans can request to follow
CREATE POLICY "Fans can request to follow"
    ON fan_follows FOR INSERT
    WITH CHECK (
        fan_id = auth.uid()
        AND initiated_by = auth.uid()
        AND status = 'pending'
    );

-- Fan follows: Fans can respond to follow invites
-- Check that the swimmer (via user_id) initiated this invite
CREATE POLICY "Fans can respond to follow invites"
    ON fan_follows FOR UPDATE
    USING (
        fan_id = auth.uid()
        AND status = 'pending'
        AND initiated_by IN (SELECT user_id FROM swimmers WHERE id = swimmer_id)
    )
    WITH CHECK (status IN ('approved', 'denied'));

-- Fan follows: Fans can view own follows
CREATE POLICY "Fans can view own follows"
    ON fan_follows FOR SELECT
    USING (fan_id = auth.uid());

-- Fan follows: Fans can unfollow
CREATE POLICY "Fans can unfollow"
    ON fan_follows FOR DELETE
    USING (fan_id = auth.uid() AND status = 'approved');

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Show sample IDs from each table
DO $$
BEGIN
    RAISE NOTICE 'Short IDs migration complete. Sample IDs:';
END $$;

SELECT 'teams' as table_name, id, name FROM teams LIMIT 2;
SELECT 'swimmers' as table_name, id, first_name FROM swimmers LIMIT 2;
SELECT 'events' as table_name, id, stroke::text, distance FROM events LIMIT 2;
