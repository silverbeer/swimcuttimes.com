-- Seed data for Elise's swimming
-- Run with: psql $DATABASE_URL -f supabase/seed_elise.sql
-- Or via Supabase Studio SQL editor

-- =============================================================================
-- TEAMS
-- =============================================================================

-- Worcester Academy (Prep School - NEPSAC)
INSERT INTO teams (id, name, team_type, sanctioning_body, state) VALUES
    ('worcacademy1', 'Worcester Academy', 'high_school', 'NEPSAC', 'MA')
ON CONFLICT DO NOTHING;

-- Greenwood Swimming (USA Swimming Club)
INSERT INTO teams (id, name, team_type, sanctioning_body, lsc) VALUES
    ('greenwoodsw1', 'Greenwood Swimming', 'club', 'USA Swimming', 'NE')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- SWIMMER: ELISE
-- =============================================================================
-- NOTE: Update date_of_birth to Elise's actual DOB

INSERT INTO swimmers (id, first_name, last_name, date_of_birth, gender) VALUES
    ('elise0000001', 'Elise', 'Swimmer', '2008-01-01', 'F')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- TEAM ASSIGNMENTS
-- =============================================================================

-- Elise on Worcester Academy (current)
INSERT INTO swimmer_teams (swimmer_id, team_id, start_date) VALUES
    ('elise0000001', 'worcacademy1', '2024-09-01')
ON CONFLICT DO NOTHING;

-- Elise on Greenwood Swimming (current)
INSERT INTO swimmer_teams (swimmer_id, team_id, start_date) VALUES
    ('elise0000001', 'greenwoodsw1', '2024-09-01')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- TIME STANDARDS: NE Swimming Senior Championship 2025 SCY (Girls)
-- =============================================================================
-- Qualifying period: March 1, 2024 through entry deadline
-- Source: 2025 SCY New England Senior Championship Time Standards

-- Helper to insert time standards using event lookup
DO $$
DECLARE
    v_standard_name TEXT := 'NE Senior Championship';
    v_cut_level TEXT := 'Senior Cut';
    v_sanctioning_body TEXT := 'NE Swimming';
    v_effective_year INT := 2025;
    v_qualifying_start DATE := '2024-03-01';
    v_gender gender := 'F';
BEGIN
    -- 50 Freestyle: 25.49
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 2549, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'freestyle' AND distance = 50 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 100 Freestyle: 54.69
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 5469, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'freestyle' AND distance = 100 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 200 Freestyle: 1:58.09
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 11809, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'freestyle' AND distance = 200 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 500 Freestyle: 5:18.09
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 31809, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'freestyle' AND distance = 500 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 1000 Freestyle: 10:58.69
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 65869, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'freestyle' AND distance = 1000 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 1650 Freestyle: 18:28.99
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 110899, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'freestyle' AND distance = 1650 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 100 Backstroke: 1:02.19
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 6219, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'backstroke' AND distance = 100 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 200 Backstroke: 2:12.59
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 13259, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'backstroke' AND distance = 200 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 100 Breaststroke: 1:11.19
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 7119, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'breaststroke' AND distance = 100 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 200 Breaststroke: 2:32.79
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 15279, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'breaststroke' AND distance = 200 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 100 Butterfly: 1:00.59
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 6059, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'butterfly' AND distance = 100 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 200 Butterfly: 2:17.89
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 13789, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'butterfly' AND distance = 200 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 200 IM: 2:13.99
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 13399, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'im' AND distance = 200 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- 400 IM: 4:46.59
    INSERT INTO time_standards (event_id, gender, standard_name, cut_level, sanctioning_body, time_centiseconds, qualifying_start, effective_year)
    SELECT id, v_gender, v_standard_name, v_cut_level, v_sanctioning_body, 28659, v_qualifying_start, v_effective_year
    FROM events WHERE stroke = 'im' AND distance = 400 AND course = 'scy'
    ON CONFLICT DO NOTHING;

    -- Note: 50 BK, 50 BR, 50 FL require "100 Qualifying Time" (no separate 50 cut)
END $$;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify Elise was created
SELECT 'Swimmer' as type, first_name, last_name, gender::text, date_of_birth::text
FROM swimmers WHERE first_name = 'Elise';

-- Verify teams
SELECT 'Team' as type, name, team_type::text, sanctioning_body
FROM teams WHERE name IN ('Worcester Academy', 'Greenwood Swimming');

-- Verify team assignments
SELECT 'Assignment' as type, s.first_name, t.name as team, st.start_date::text
FROM swimmer_teams st
JOIN swimmers s ON st.swimmer_id = s.id
JOIN teams t ON st.team_id = t.id
WHERE s.first_name = 'Elise';

-- Verify time standards
SELECT
    e.distance || ' ' || e.stroke::text as event,
    format_swim_time(ts.time_centiseconds) as cut_time,
    ts.standard_name
FROM time_standards ts
JOIN events e ON ts.event_id = e.id
WHERE ts.sanctioning_body = 'NE Swimming'
  AND ts.gender = 'F'
  AND e.course = 'scy'
ORDER BY e.stroke, e.distance;
