-- Seed data for swimcuttimes
-- This file populates standard events used in competitive swimming

-- =============================================================================
-- STANDARD EVENTS
-- =============================================================================

-- SCY Events (Short Course Yards)
INSERT INTO events (stroke, distance, course) VALUES
    ('freestyle', 50, 'scy'),
    ('freestyle', 100, 'scy'),
    ('freestyle', 200, 'scy'),
    ('freestyle', 500, 'scy'),
    ('freestyle', 1000, 'scy'),
    ('freestyle', 1650, 'scy'),
    ('backstroke', 50, 'scy'),
    ('backstroke', 100, 'scy'),
    ('backstroke', 200, 'scy'),
    ('breaststroke', 50, 'scy'),
    ('breaststroke', 100, 'scy'),
    ('breaststroke', 200, 'scy'),
    ('butterfly', 50, 'scy'),
    ('butterfly', 100, 'scy'),
    ('butterfly', 200, 'scy'),
    ('im', 100, 'scy'),
    ('im', 200, 'scy'),
    ('im', 400, 'scy')
ON CONFLICT (stroke, distance, course) DO NOTHING;

-- SCM Events (Short Course Meters)
INSERT INTO events (stroke, distance, course) VALUES
    ('freestyle', 50, 'scm'),
    ('freestyle', 100, 'scm'),
    ('freestyle', 200, 'scm'),
    ('freestyle', 400, 'scm'),
    ('freestyle', 800, 'scm'),
    ('freestyle', 1500, 'scm'),
    ('backstroke', 50, 'scm'),
    ('backstroke', 100, 'scm'),
    ('backstroke', 200, 'scm'),
    ('breaststroke', 50, 'scm'),
    ('breaststroke', 100, 'scm'),
    ('breaststroke', 200, 'scm'),
    ('butterfly', 50, 'scm'),
    ('butterfly', 100, 'scm'),
    ('butterfly', 200, 'scm'),
    ('im', 100, 'scm'),
    ('im', 200, 'scm'),
    ('im', 400, 'scm')
ON CONFLICT (stroke, distance, course) DO NOTHING;

-- LCM Events (Long Course Meters)
INSERT INTO events (stroke, distance, course) VALUES
    ('freestyle', 50, 'lcm'),
    ('freestyle', 100, 'lcm'),
    ('freestyle', 200, 'lcm'),
    ('freestyle', 400, 'lcm'),
    ('freestyle', 800, 'lcm'),
    ('freestyle', 1500, 'lcm'),
    ('backstroke', 50, 'lcm'),
    ('backstroke', 100, 'lcm'),
    ('backstroke', 200, 'lcm'),
    ('breaststroke', 50, 'lcm'),
    ('breaststroke', 100, 'lcm'),
    ('breaststroke', 200, 'lcm'),
    ('butterfly', 50, 'lcm'),
    ('butterfly', 100, 'lcm'),
    ('butterfly', 200, 'lcm'),
    ('im', 200, 'lcm'),
    ('im', 400, 'lcm')
ON CONFLICT (stroke, distance, course) DO NOTHING;

-- =============================================================================
-- SAMPLE TEAM
-- =============================================================================

INSERT INTO teams (id, name, team_type, sanctioning_body, lsc) VALUES
    ('00000000-0000-0000-0000-000000000001', 'New England Swimming', 'club', 'USA Swimming', 'NE')
ON CONFLICT DO NOTHING;
