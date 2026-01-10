-- =============================================================================
-- SEED DATA FOR RACING SUITS
-- Common tech suits and regular racing suits from major brands
-- =============================================================================

-- =============================================================================
-- TECH SUITS - Men's (Jammer)
-- =============================================================================

INSERT INTO suit_models (brand, model_name, suit_type, is_tech_suit, gender, release_year, msrp_cents, expected_races_peak, expected_races_total, fina_approved) VALUES
-- Speedo
('Speedo', 'LZR Pure Intent', 'jammer', true, 'M', 2020, 54900, 10, 35, true),
('Speedo', 'LZR Pure Valor', 'jammer', true, 'M', 2022, 37500, 10, 35, true),
('Speedo', 'Fastskin LZR Racer X', 'jammer', true, 'M', 2019, 45000, 10, 35, true),
-- Arena
('Arena', 'Carbon Core FX', 'jammer', true, 'M', 2020, 45000, 10, 35, true),
('Arena', 'Carbon Glide', 'jammer', true, 'M', 2021, 55000, 10, 35, true),
('Arena', 'Primo', 'jammer', true, 'M', 2023, 39900, 10, 35, true),
('Arena', 'Carbon Air2', 'jammer', true, 'M', 2019, 50000, 10, 35, true),
-- TYR
('TYR', 'Venzo Genesis', 'jammer', true, 'M', 2023, 47500, 10, 35, true),
('TYR', 'Avictor Supernova', 'jammer', true, 'M', 2021, 40000, 10, 35, true),
('TYR', 'Venzo Camo', 'jammer', true, 'M', 2022, 47500, 10, 35, true),
-- Mizuno
('Mizuno', 'GX Sonic V MR', 'jammer', true, 'M', 2022, 45000, 10, 35, true),
('Mizuno', 'GX Sonic V ST', 'jammer', true, 'M', 2022, 35000, 10, 35, true),
-- Finis
('Finis', 'Rival 2.0', 'jammer', true, 'M', 2021, 29900, 10, 35, true);

-- =============================================================================
-- TECH SUITS - Women's (Kneeskin)
-- =============================================================================

INSERT INTO suit_models (brand, model_name, suit_type, is_tech_suit, gender, release_year, msrp_cents, expected_races_peak, expected_races_total, fina_approved) VALUES
-- Speedo
('Speedo', 'LZR Pure Intent', 'kneeskin', true, 'F', 2020, 54900, 10, 35, true),
('Speedo', 'LZR Pure Valor', 'kneeskin', true, 'F', 2022, 37500, 10, 35, true),
('Speedo', 'Fastskin LZR Racer X', 'kneeskin', true, 'F', 2019, 55000, 10, 35, true),
-- Arena
('Arena', 'Carbon Core FX', 'kneeskin', true, 'F', 2020, 55000, 10, 35, true),
('Arena', 'Carbon Glide', 'kneeskin', true, 'F', 2021, 65000, 10, 35, true),
('Arena', 'Primo', 'kneeskin', true, 'F', 2023, 49900, 10, 35, true),
('Arena', 'Carbon Air2', 'kneeskin', true, 'F', 2019, 60000, 10, 35, true),
-- TYR
('TYR', 'Venzo Genesis', 'kneeskin', true, 'F', 2023, 55000, 10, 35, true),
('TYR', 'Avictor Supernova', 'kneeskin', true, 'F', 2021, 50000, 10, 35, true),
('TYR', 'Venzo Camo', 'kneeskin', true, 'F', 2022, 55000, 10, 35, true),
-- Mizuno
('Mizuno', 'GX Sonic V MR', 'kneeskin', true, 'F', 2022, 55000, 10, 35, true),
('Mizuno', 'GX Sonic V ST', 'kneeskin', true, 'F', 2022, 45000, 10, 35, true),
-- Finis
('Finis', 'Rival 2.0', 'kneeskin', true, 'F', 2021, 34900, 10, 35, true);

-- =============================================================================
-- REGULAR RACING SUITS - Men's (Jammer)
-- =============================================================================

INSERT INTO suit_models (brand, model_name, suit_type, is_tech_suit, gender, release_year, msrp_cents, expected_races_peak, expected_races_total, fina_approved) VALUES
-- Speedo
('Speedo', 'Endurance+ Jammer', 'jammer', false, 'M', 2023, 4800, 50, 150, true),
('Speedo', 'ProLT Jammer', 'jammer', false, 'M', 2023, 3500, 50, 150, true),
('Speedo', 'Solid Jammer', 'jammer', false, 'M', 2023, 3000, 50, 150, true),
-- TYR
('TYR', 'Durafast Elite Jammer', 'jammer', false, 'M', 2023, 4500, 50, 150, true),
('TYR', 'Durafast One Jammer', 'jammer', false, 'M', 2023, 3500, 50, 150, true),
('TYR', 'Hexa Jammer', 'jammer', false, 'M', 2023, 2800, 50, 150, true),
-- Arena
('Arena', 'Solid Jammer', 'jammer', false, 'M', 2023, 3500, 50, 150, true),
('Arena', 'MaxLife Jammer', 'jammer', false, 'M', 2023, 4000, 50, 150, true),
('Arena', 'Team Jammer', 'jammer', false, 'M', 2023, 2500, 50, 150, true);

-- =============================================================================
-- REGULAR RACING SUITS - Women's (Kneeskin and Brief)
-- =============================================================================

INSERT INTO suit_models (brand, model_name, suit_type, is_tech_suit, gender, release_year, msrp_cents, expected_races_peak, expected_races_total, fina_approved) VALUES
-- Speedo - Kneeskin
('Speedo', 'Endurance+ Kneeskin', 'kneeskin', false, 'F', 2023, 6500, 50, 150, true),
('Speedo', 'ProLT Kneeskin', 'kneeskin', false, 'F', 2023, 5500, 50, 150, true),
-- TYR - Kneeskin
('TYR', 'Durafast Elite Diamondfit', 'kneeskin', false, 'F', 2023, 6000, 50, 150, true),
('TYR', 'Durafast One Diamondfit', 'kneeskin', false, 'F', 2023, 4500, 50, 150, true),
-- Arena - Kneeskin
('Arena', 'Powerskin ST', 'kneeskin', false, 'F', 2023, 6500, 50, 150, true),
-- Speedo - Brief/Flyback
('Speedo', 'Flyback', 'brief', false, 'F', 2023, 4000, 50, 150, true),
('Speedo', 'Endurance+ Flyback', 'brief', false, 'F', 2023, 5000, 50, 150, true),
-- TYR - Brief
('TYR', 'Cutoutfit', 'brief', false, 'F', 2023, 4200, 50, 150, true),
-- Arena - Brief
('Arena', 'Powerskin Brief', 'brief', false, 'F', 2023, 4500, 50, 150, true);

-- =============================================================================
-- MEN'S BRIEF (for sprinters)
-- =============================================================================

INSERT INTO suit_models (brand, model_name, suit_type, is_tech_suit, gender, release_year, msrp_cents, expected_races_peak, expected_races_total, fina_approved) VALUES
('Speedo', 'Endurance+ Brief', 'brief', false, 'M', 2023, 3000, 50, 150, true),
('TYR', 'Durafast Elite Brief', 'brief', false, 'M', 2023, 3200, 50, 150, true),
('Arena', 'Solid Brief', 'brief', false, 'M', 2023, 2800, 50, 150, true);
