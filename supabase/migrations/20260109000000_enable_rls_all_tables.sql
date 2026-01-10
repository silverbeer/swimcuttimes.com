-- =============================================================================
-- ENABLE ROW LEVEL SECURITY ON ALL TABLES
-- Addresses Supabase security warnings for tables exposed to PostgREST
-- =============================================================================

-- =============================================================================
-- TEAMS
-- =============================================================================

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;

-- Public read access (swimming data is public)
CREATE POLICY "Teams are publicly readable"
    ON teams FOR SELECT
    USING (true);

-- Admins and coaches can insert
CREATE POLICY "Admins and coaches can create teams"
    ON teams FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

-- Admins and coaches can update
CREATE POLICY "Admins and coaches can update teams"
    ON teams FOR UPDATE
    USING (is_admin() OR is_coach());

-- Only admins can delete
CREATE POLICY "Only admins can delete teams"
    ON teams FOR DELETE
    USING (is_admin());

-- =============================================================================
-- SWIMMERS
-- =============================================================================

ALTER TABLE swimmers ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Swimmers are publicly readable"
    ON swimmers FOR SELECT
    USING (true);

-- Admins and coaches can insert
CREATE POLICY "Admins and coaches can create swimmers"
    ON swimmers FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

-- Admins and coaches can update any swimmer
CREATE POLICY "Admins and coaches can update swimmers"
    ON swimmers FOR UPDATE
    USING (is_admin() OR is_coach());

-- Swimmers can update their own record (if linked via user_id)
CREATE POLICY "Swimmers can update own record"
    ON swimmers FOR UPDATE
    USING (user_id = auth.uid());

-- Only admins can delete
CREATE POLICY "Only admins can delete swimmers"
    ON swimmers FOR DELETE
    USING (is_admin());

-- =============================================================================
-- SWIMMER_TEAMS
-- =============================================================================

ALTER TABLE swimmer_teams ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Swimmer team memberships are publicly readable"
    ON swimmer_teams FOR SELECT
    USING (true);

-- Admins and coaches can manage
CREATE POLICY "Admins and coaches can create swimmer team memberships"
    ON swimmer_teams FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can update swimmer team memberships"
    ON swimmer_teams FOR UPDATE
    USING (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can delete swimmer team memberships"
    ON swimmer_teams FOR DELETE
    USING (is_admin() OR is_coach());

-- =============================================================================
-- EVENTS
-- =============================================================================

ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Public read access (reference data)
CREATE POLICY "Events are publicly readable"
    ON events FOR SELECT
    USING (true);

-- Only admins can manage events (reference data)
CREATE POLICY "Only admins can create events"
    ON events FOR INSERT
    WITH CHECK (is_admin());

CREATE POLICY "Only admins can update events"
    ON events FOR UPDATE
    USING (is_admin());

CREATE POLICY "Only admins can delete events"
    ON events FOR DELETE
    USING (is_admin());

-- =============================================================================
-- MEETS
-- =============================================================================

ALTER TABLE meets ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Meets are publicly readable"
    ON meets FOR SELECT
    USING (true);

-- Admins and coaches can manage
CREATE POLICY "Admins and coaches can create meets"
    ON meets FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can update meets"
    ON meets FOR UPDATE
    USING (is_admin() OR is_coach());

CREATE POLICY "Only admins can delete meets"
    ON meets FOR DELETE
    USING (is_admin());

-- =============================================================================
-- TIME_STANDARDS
-- =============================================================================

ALTER TABLE time_standards ENABLE ROW LEVEL SECURITY;

-- Public read access (reference data)
CREATE POLICY "Time standards are publicly readable"
    ON time_standards FOR SELECT
    USING (true);

-- Only admins can manage time standards (reference data)
CREATE POLICY "Only admins can create time standards"
    ON time_standards FOR INSERT
    WITH CHECK (is_admin());

CREATE POLICY "Only admins can update time standards"
    ON time_standards FOR UPDATE
    USING (is_admin());

CREATE POLICY "Only admins can delete time standards"
    ON time_standards FOR DELETE
    USING (is_admin());

-- =============================================================================
-- SWIM_TIMES
-- =============================================================================

ALTER TABLE swim_times ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Swim times are publicly readable"
    ON swim_times FOR SELECT
    USING (true);

-- Admins and coaches can manage
CREATE POLICY "Admins and coaches can create swim times"
    ON swim_times FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can update swim times"
    ON swim_times FOR UPDATE
    USING (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can delete swim times"
    ON swim_times FOR DELETE
    USING (is_admin() OR is_coach());

-- =============================================================================
-- SPLITS
-- =============================================================================

ALTER TABLE splits ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Splits are publicly readable"
    ON splits FOR SELECT
    USING (true);

-- Admins and coaches can manage
CREATE POLICY "Admins and coaches can create splits"
    ON splits FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can update splits"
    ON splits FOR UPDATE
    USING (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can delete splits"
    ON splits FOR DELETE
    USING (is_admin() OR is_coach());

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON POLICY "Teams are publicly readable" ON teams IS
    'Swimming team data is public information';

COMMENT ON POLICY "Swimmers are publicly readable" ON swimmers IS
    'Swimmer profiles are public (competitive swimming is public record)';

COMMENT ON POLICY "Swim times are publicly readable" ON swim_times IS
    'Race results are public record';
