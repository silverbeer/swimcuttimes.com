-- Meet-Team associations (many-to-many)
-- Tracks which teams participate in a meet

CREATE TABLE meet_teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meet_id UUID NOT NULL REFERENCES meets(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    is_host BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate team entries per meet
    CONSTRAINT unique_meet_team UNIQUE (meet_id, team_id)
);

-- Indexes for efficient lookups
CREATE INDEX idx_meet_teams_meet ON meet_teams(meet_id);
CREATE INDEX idx_meet_teams_team ON meet_teams(team_id);

-- Enable Row Level Security
ALTER TABLE meet_teams ENABLE ROW LEVEL SECURITY;

-- Public read access (meet participation is public info)
CREATE POLICY "Meet teams are publicly readable"
    ON meet_teams FOR SELECT
    USING (true);

-- Admins and coaches can add teams to meets
CREATE POLICY "Admins and coaches can create meet teams"
    ON meet_teams FOR INSERT
    WITH CHECK (public.is_admin() OR public.is_coach());

-- Admins and coaches can update (e.g., change host status)
CREATE POLICY "Admins and coaches can update meet teams"
    ON meet_teams FOR UPDATE
    USING (public.is_admin() OR public.is_coach());

-- Admins and coaches can remove teams from meets
CREATE POLICY "Admins and coaches can delete meet teams"
    ON meet_teams FOR DELETE
    USING (public.is_admin() OR public.is_coach());
