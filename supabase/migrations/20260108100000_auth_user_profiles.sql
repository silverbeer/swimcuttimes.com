-- =============================================================================
-- USER PROFILES
-- Extends Supabase auth.users with application-specific data
-- =============================================================================

-- Role enum for type safety
CREATE TYPE user_role AS ENUM ('admin', 'coach', 'swimmer', 'fan');

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role user_role NOT NULL DEFAULT 'fan',

    -- Display info
    display_name TEXT,
    avatar_url TEXT,

    -- For swimmers/coaches: link to swimmer record
    swimmer_id UUID REFERENCES swimmers(id) ON DELETE SET NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Soft delete for audit trail
    deleted_at TIMESTAMPTZ
);

-- Index for role-based queries
CREATE INDEX idx_user_profiles_role ON user_profiles(role) WHERE deleted_at IS NULL;

-- Index for swimmer lookup
CREATE INDEX idx_user_profiles_swimmer ON user_profiles(swimmer_id) WHERE swimmer_id IS NOT NULL;

-- =============================================================================
-- AUTO-CREATE PROFILE ON SIGNUP
-- =============================================================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users insert
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

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

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- HELPER FUNCTION FOR RLS (avoids infinite recursion)
-- =============================================================================

-- This function bypasses RLS to check user role
CREATE OR REPLACE FUNCTION get_user_role(user_id UUID)
RETURNS user_role AS $$
DECLARE
    result user_role;
BEGIN
    SELECT role INTO result
    FROM user_profiles
    WHERE id = user_id AND deleted_at IS NULL;
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN get_user_role(auth.uid()) = 'admin';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION is_coach()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN get_user_role(auth.uid()) = 'coach';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

-- Admins can view all profiles
CREATE POLICY "Admins can view all profiles"
    ON user_profiles FOR SELECT
    USING (is_admin());

-- Coaches can view swimmers on their teams
CREATE POLICY "Coaches can view team swimmers"
    ON user_profiles FOR SELECT
    USING (is_coach() AND role = 'swimmer');

-- Users can update their own profile (limited fields)
CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Only admins can update roles
CREATE POLICY "Admins can update any profile"
    ON user_profiles FOR UPDATE
    USING (is_admin());

COMMENT ON TABLE user_profiles IS 'Application user profiles extending Supabase auth';
COMMENT ON COLUMN user_profiles.role IS 'User role: admin, coach, swimmer, or fan';
COMMENT ON COLUMN user_profiles.swimmer_id IS 'Links user to swimmer record (for swimmers/coaches who are also swimmers)';
