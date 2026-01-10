-- =============================================================================
-- RACING SUIT TRACKING
-- Track all racing suits (tech suits and regular racing suits) for swimmers
-- =============================================================================

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

CREATE TYPE suit_type AS ENUM ('jammer', 'kneeskin', 'brief');
CREATE TYPE suit_condition AS ENUM ('new', 'good', 'worn', 'retired');

-- =============================================================================
-- SUIT_MODELS (Catalog of all racing suit products)
-- =============================================================================

CREATE TABLE suit_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand TEXT NOT NULL,                       -- e.g., "Speedo", "Arena", "TYR"
    model_name TEXT NOT NULL,                  -- e.g., "LZR Pure Intent", "Carbon Core FX"
    suit_type suit_type NOT NULL,
    is_tech_suit BOOLEAN NOT NULL DEFAULT false, -- True for tech suits, false for regular racing suits
    gender gender NOT NULL,
    release_year INTEGER,                      -- Year the suit was released
    msrp_cents INTEGER,                        -- Manufacturer's suggested retail price in cents
    expected_races_peak INTEGER DEFAULT 10,    -- Races at peak performance (10 for tech, 50 for regular)
    expected_races_total INTEGER DEFAULT 30,   -- Total expected races (30 for tech, 150 for regular)
    fina_approved BOOLEAN DEFAULT true,        -- Whether suit is FINA approved for competition
    notes TEXT,                                -- Additional notes about the suit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Each suit model is unique per brand, model, type, and gender
    CONSTRAINT unique_suit_model UNIQUE (brand, model_name, suit_type, gender)
);

CREATE INDEX idx_suit_models_brand ON suit_models(brand);
CREATE INDEX idx_suit_models_is_tech_suit ON suit_models(is_tech_suit);
CREATE INDEX idx_suit_models_gender ON suit_models(gender);
CREATE INDEX idx_suit_models_fina ON suit_models(fina_approved);

-- =============================================================================
-- SWIMMER_SUITS (Swimmer's personal suit inventory)
-- =============================================================================

CREATE TABLE swimmer_suits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swimmer_id UUID NOT NULL REFERENCES swimmers(id) ON DELETE CASCADE,
    suit_model_id UUID NOT NULL REFERENCES suit_models(id),
    nickname TEXT,                             -- e.g., "Lucky Suit", "Championship Suit"
    size TEXT,                                 -- e.g., "26", "28", "30"
    color TEXT,                                -- e.g., "Black/Gold", "Navy"
    purchase_date DATE,                        -- When the suit was purchased
    purchase_price_cents INTEGER,              -- Actual price paid in cents
    purchase_location TEXT,                    -- e.g., "SwimOutlet", "Dick's", "Team order"
    wear_count INTEGER DEFAULT 0,              -- Total times worn (practice + races)
    race_count INTEGER DEFAULT 0,              -- Number of races in this suit
    condition suit_condition DEFAULT 'new',
    retired_date DATE,                         -- Date suit was retired
    retirement_reason TEXT,                    -- e.g., "Lost compression", "Seam rip"
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_swimmer_suits_swimmer ON swimmer_suits(swimmer_id);
CREATE INDEX idx_swimmer_suits_model ON swimmer_suits(suit_model_id);
CREATE INDEX idx_swimmer_suits_condition ON swimmer_suits(condition);
CREATE INDEX idx_swimmer_suits_active ON swimmer_suits(swimmer_id) WHERE condition != 'retired';

-- =============================================================================
-- ADD SUIT_ID TO SWIM_TIMES
-- =============================================================================

ALTER TABLE swim_times ADD COLUMN suit_id UUID REFERENCES swimmer_suits(id);

CREATE INDEX idx_swim_times_suit ON swim_times(suit_id);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

-- SUIT_MODELS (reference data)
ALTER TABLE suit_models ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Suit models are publicly readable"
    ON suit_models FOR SELECT
    USING (true);

CREATE POLICY "Only admins can create suit models"
    ON suit_models FOR INSERT
    WITH CHECK (is_admin());

CREATE POLICY "Only admins can update suit models"
    ON suit_models FOR UPDATE
    USING (is_admin());

CREATE POLICY "Only admins can delete suit models"
    ON suit_models FOR DELETE
    USING (is_admin());

-- SWIMMER_SUITS
ALTER TABLE swimmer_suits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Swimmer suits are publicly readable"
    ON swimmer_suits FOR SELECT
    USING (true);

CREATE POLICY "Admins and coaches can create swimmer suits"
    ON swimmer_suits FOR INSERT
    WITH CHECK (is_admin() OR is_coach());

CREATE POLICY "Admins and coaches can update swimmer suits"
    ON swimmer_suits FOR UPDATE
    USING (is_admin() OR is_coach());

-- Swimmers can update their own suits
CREATE POLICY "Swimmers can update own suits"
    ON swimmer_suits FOR UPDATE
    USING (
        swimmer_id IN (
            SELECT id FROM swimmers WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Admins and coaches can delete swimmer suits"
    ON swimmer_suits FOR DELETE
    USING (is_admin() OR is_coach());

-- =============================================================================
-- TRIGGER TO INCREMENT RACE_COUNT
-- Auto-increment race_count when a swim_time is recorded with this suit
-- =============================================================================

CREATE OR REPLACE FUNCTION increment_suit_race_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.suit_id IS NOT NULL THEN
        UPDATE swimmer_suits
        SET race_count = race_count + 1,
            updated_at = NOW()
        WHERE id = NEW.suit_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

CREATE TRIGGER trigger_increment_suit_race_count
    AFTER INSERT ON swim_times
    FOR EACH ROW
    EXECUTE FUNCTION increment_suit_race_count();

-- =============================================================================
-- UPDATED_AT TRIGGER FOR NEW TABLES
-- =============================================================================

CREATE TRIGGER update_suit_models_updated_at BEFORE UPDATE ON suit_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_swimmer_suits_updated_at BEFORE UPDATE ON swimmer_suits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE suit_models IS 'Catalog of all racing suit products (tech suits and regular racing suits)';
COMMENT ON TABLE swimmer_suits IS 'Individual suits owned by swimmers';
COMMENT ON COLUMN suit_models.is_tech_suit IS 'True for tech suits ($200-$500+), false for regular racing suits ($30-$100)';
COMMENT ON COLUMN suit_models.expected_races_peak IS 'Number of races suit maintains peak performance (6-12 for tech suits, 50+ for regular)';
COMMENT ON COLUMN suit_models.fina_approved IS 'Whether suit meets FINA regulations for sanctioned competition';
COMMENT ON COLUMN swimmer_suits.purchase_location IS 'Where the suit was purchased (SwimOutlet, Dick''s, Team order, etc.)';
COMMENT ON COLUMN swim_times.suit_id IS 'Optional reference to the suit worn during this race';
