-- Fix mutable search_path security issue on all public functions
-- Using ALTER FUNCTION to set search_path without changing function signatures

-- Utility functions (from initial_schema.sql)
ALTER FUNCTION public.format_swim_time(INTEGER) SET search_path = '';
ALTER FUNCTION public.parse_swim_time(TEXT) SET search_path = '';
ALTER FUNCTION public.update_updated_at() SET search_path = '';

-- Split interval function (from add_splits.sql)
ALTER FUNCTION public.get_split_interval(UUID, INTEGER) SET search_path = '';

-- Auth functions (from auth_user_profiles.sql)
ALTER FUNCTION public.handle_new_user() SET search_path = '';
ALTER FUNCTION public.get_user_role(UUID) SET search_path = '';
ALTER FUNCTION public.is_admin() SET search_path = '';
ALTER FUNCTION public.is_coach() SET search_path = '';

-- Invitation functions (from auth_invitations.sql)
ALTER FUNCTION public.validate_invite_permission() SET search_path = '';
ALTER FUNCTION public.expire_old_invitations() SET search_path = '';

-- Follow validation (from auth_fan_follows.sql)
ALTER FUNCTION public.validate_fan_follow() SET search_path = '';
