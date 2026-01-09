-- Add unique constraint on team name
-- Prevents duplicate team names which cause confusion

-- First, remove any existing duplicates (keep the oldest one)
DELETE FROM teams a USING teams b
WHERE a.id > b.id AND a.name = b.name;

-- Add unique constraint
ALTER TABLE teams ADD CONSTRAINT unique_team_name UNIQUE (name);
