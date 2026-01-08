-- Initial schema for swimcuttimes
-- Creates all core tables for tracking swimmers, teams, meets, times, and standards

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

CREATE TYPE gender AS ENUM ('M', 'F');
CREATE TYPE course AS ENUM ('scy', 'scm', 'lcm');
CREATE TYPE stroke AS ENUM ('freestyle', 'backstroke', 'breaststroke', 'butterfly', 'im');
CREATE TYPE team_type AS ENUM ('club', 'high_school', 'college', 'national', 'olympic');
CREATE TYPE meet_type AS ENUM ('championship', 'invitational', 'dual', 'time_trial');
CREATE TYPE round AS ENUM ('prelims', 'finals', 'consolation', 'bonus_finals', 'time_trial');

-- =============================================================================
-- TEAMS
-- =============================================================================

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    team_type team_type NOT NULL,
    sanctioning_body TEXT NOT NULL,  -- e.g., "USA Swimming", "NCAA D1", "FINA"
    lsc TEXT,                        -- LSC code for club teams (e.g., "NE", "PV")
    division TEXT,                   -- For college teams (e.g., "D1", "D2", "D3")
    state TEXT,                      -- State for high school teams
    country TEXT DEFAULT 'USA',      -- Country code for national/olympic teams
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_teams_type ON teams(team_type);
CREATE INDEX idx_teams_sanctioning_body ON teams(sanctioning_body);

-- =============================================================================
-- SWIMMERS
-- =============================================================================

CREATE TABLE swimmers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    gender gender NOT NULL,
    user_id UUID REFERENCES auth.users(id),  -- Link to Supabase Auth user
    usa_swimming_id TEXT,
    swimcloud_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_swimmers_name ON swimmers(last_name, first_name);
CREATE INDEX idx_swimmers_user ON swimmers(user_id);
CREATE INDEX idx_swimmers_usa_swimming_id ON swimmers(usa_swimming_id);

-- =============================================================================
-- SWIMMER-TEAM ASSOCIATIONS (many-to-many with temporal data)
-- =============================================================================

CREATE TABLE swimmer_teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swimmer_id UUID NOT NULL REFERENCES swimmers(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE,  -- NULL = current membership
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate active memberships for same swimmer/team
    CONSTRAINT unique_active_membership UNIQUE (swimmer_id, team_id, start_date)
);

CREATE INDEX idx_swimmer_teams_swimmer ON swimmer_teams(swimmer_id);
CREATE INDEX idx_swimmer_teams_team ON swimmer_teams(team_id);
CREATE INDEX idx_swimmer_teams_dates ON swimmer_teams(start_date, end_date);

-- =============================================================================
-- EVENTS
-- =============================================================================

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stroke stroke NOT NULL,
    distance INTEGER NOT NULL,
    course course NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Each event is unique
    CONSTRAINT unique_event UNIQUE (stroke, distance, course)
);

CREATE INDEX idx_events_stroke ON events(stroke);
CREATE INDEX idx_events_course ON events(course);

-- =============================================================================
-- MEETS
-- =============================================================================

CREATE TABLE meets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    location TEXT NOT NULL,  -- Venue name
    city TEXT NOT NULL,
    state TEXT,
    country TEXT DEFAULT 'USA',
    start_date DATE NOT NULL,
    end_date DATE,  -- NULL for single-day meets
    course course NOT NULL,
    lanes INTEGER NOT NULL CHECK (lanes IN (6, 8, 10)),
    indoor BOOLEAN DEFAULT TRUE,
    sanctioning_body TEXT NOT NULL,
    meet_type meet_type NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meets_date ON meets(start_date);
CREATE INDEX idx_meets_sanctioning_body ON meets(sanctioning_body);
CREATE INDEX idx_meets_type ON meets(meet_type);

-- =============================================================================
-- TIME STANDARDS
-- =============================================================================

CREATE TABLE time_standards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    gender gender NOT NULL,
    age_group TEXT,  -- e.g., "10U", "11-12", "15-18", "Open", NULL = no restriction
    standard_name TEXT NOT NULL,  -- e.g., "Silver Championship", "Futures"
    cut_level TEXT NOT NULL,  -- e.g., "Cut Time", "Cut Off Time", "A", "AA"
    sanctioning_body TEXT NOT NULL,  -- e.g., "NE Swimming", "USA Swimming"
    time_centiseconds INTEGER NOT NULL,  -- Time in centiseconds
    qualifying_start DATE,
    qualifying_end DATE,
    effective_year INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_time_standards_event ON time_standards(event_id);
CREATE INDEX idx_time_standards_gender ON time_standards(gender);
CREATE INDEX idx_time_standards_age_group ON time_standards(age_group);
CREATE INDEX idx_time_standards_sanctioning ON time_standards(sanctioning_body);
CREATE INDEX idx_time_standards_year ON time_standards(effective_year);
CREATE INDEX idx_time_standards_lookup ON time_standards(event_id, gender, age_group, sanctioning_body);

-- =============================================================================
-- SWIM TIMES
-- =============================================================================

CREATE TABLE swim_times (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swimmer_id UUID NOT NULL REFERENCES swimmers(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id),
    meet_id UUID NOT NULL REFERENCES meets(id),
    team_id UUID NOT NULL REFERENCES teams(id),  -- Team at time of swim
    time_centiseconds INTEGER NOT NULL,  -- Time in centiseconds
    swim_date DATE NOT NULL,
    round round,
    lane INTEGER CHECK (lane >= 1 AND lane <= 10),
    place INTEGER,
    official BOOLEAN DEFAULT TRUE,
    dq BOOLEAN DEFAULT FALSE,
    dq_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_swim_times_swimmer ON swim_times(swimmer_id);
CREATE INDEX idx_swim_times_event ON swim_times(event_id);
CREATE INDEX idx_swim_times_meet ON swim_times(meet_id);
CREATE INDEX idx_swim_times_date ON swim_times(swim_date);
CREATE INDEX idx_swim_times_lookup ON swim_times(swimmer_id, event_id);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to format centiseconds as time string (MM:SS.cc or SS.cc)
CREATE OR REPLACE FUNCTION format_swim_time(centiseconds INTEGER)
RETURNS TEXT AS $$
DECLARE
    total_seconds NUMERIC;
    minutes INTEGER;
    seconds NUMERIC;
BEGIN
    total_seconds := centiseconds / 100.0;
    minutes := FLOOR(total_seconds / 60);
    seconds := total_seconds - (minutes * 60);

    IF minutes > 0 THEN
        RETURN minutes || ':' || LPAD(TO_CHAR(seconds, 'FM00.00'), 5, '0');
    ELSE
        RETURN TO_CHAR(seconds, 'FM00.00');
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to parse time string to centiseconds
CREATE OR REPLACE FUNCTION parse_swim_time(time_str TEXT)
RETURNS INTEGER AS $$
DECLARE
    parts TEXT[];
    minutes INTEGER;
    seconds NUMERIC;
BEGIN
    IF time_str LIKE '%:%' THEN
        parts := string_to_array(time_str, ':');
        minutes := parts[1]::INTEGER;
        seconds := parts[2]::NUMERIC;
        RETURN ROUND((minutes * 60 + seconds) * 100);
    ELSE
        RETURN ROUND(time_str::NUMERIC * 100);
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- UPDATED_AT TRIGGER
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_swimmers_updated_at BEFORE UPDATE ON swimmers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_swimmer_teams_updated_at BEFORE UPDATE ON swimmer_teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_meets_updated_at BEFORE UPDATE ON meets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_time_standards_updated_at BEFORE UPDATE ON time_standards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_swim_times_updated_at BEFORE UPDATE ON swim_times
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
