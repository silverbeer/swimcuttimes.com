-- =============================================================================
-- SPLITS TABLE
-- Stores split times for swim_times, enabling analysis across races
-- =============================================================================

CREATE TABLE splits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swim_time_id UUID NOT NULL REFERENCES swim_times(id) ON DELETE CASCADE,
    distance INTEGER NOT NULL,  -- Cumulative distance (50, 100, 150, etc.)
    time_centiseconds INTEGER NOT NULL,  -- Cumulative time at this distance
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique split per distance per swim
    UNIQUE (swim_time_id, distance)
);

-- Index for looking up splits by swim_time
CREATE INDEX idx_splits_swim_time ON splits(swim_time_id);

-- Index for querying splits across races (e.g., "all 150m splits")
CREATE INDEX idx_splits_distance ON splits(distance);

-- Composite index for analysis queries like:
-- "Get 3rd split (150m) for all 200 Free races, sorted by time"
CREATE INDEX idx_splits_analysis ON splits(distance, time_centiseconds);

-- =============================================================================
-- HELPER FUNCTION: Get interval time for a split
-- =============================================================================

CREATE OR REPLACE FUNCTION get_split_interval(
    p_swim_time_id UUID,
    p_distance INTEGER
)
RETURNS INTEGER AS $$
DECLARE
    current_time INTEGER;
    prev_time INTEGER;
BEGIN
    -- Get current split time
    SELECT time_centiseconds INTO current_time
    FROM splits
    WHERE swim_time_id = p_swim_time_id AND distance = p_distance;

    IF current_time IS NULL THEN
        RETURN NULL;
    END IF;

    -- Get previous split time (largest distance less than current)
    SELECT time_centiseconds INTO prev_time
    FROM splits
    WHERE swim_time_id = p_swim_time_id AND distance < p_distance
    ORDER BY distance DESC
    LIMIT 1;

    -- If no previous split, interval equals cumulative (first split)
    IF prev_time IS NULL THEN
        prev_time := 0;
    END IF;

    RETURN current_time - prev_time;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_split_interval IS
    'Calculate interval time for a specific split segment';
