#!/usr/bin/env python3
"""Bootstrap script to create the first admin user.

This script bypasses the invitation system to create the initial admin.
Run this once after setting up the database.

Usage:
    cd backend && uv run python ../scripts/bootstrap_admin.py
"""

import os
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

# First admin user credentials
ADMIN_EMAIL = "tom@swimcuttimes.com"
ADMIN_PASSWORD = "admin123"
ADMIN_DISPLAY_NAME = "Tom"


def main():
    """Create the first admin user."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        print("Run: ./scripts/env.sh local")
        sys.exit(1)

    print(f"Connecting to Supabase: {supabase_url}")
    client = create_client(supabase_url, supabase_key)

    # Check if admin already exists
    existing = (
        client.table("user_profiles")
        .select("id, role")
        .eq("role", "admin")
        .execute()
    )

    if existing.data:
        print(f"Admin user already exists (count: {len(existing.data)})")
        print("Skipping bootstrap.")
        return

    print(f"Creating admin user: {ADMIN_EMAIL}")

    try:
        # Create user in Supabase Auth
        print("Calling sign_up...")
        auth_response = client.auth.sign_up(
            {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "options": {
                    "data": {
                        "display_name": ADMIN_DISPLAY_NAME,
                    },
                    "email_redirect_to": None,
                },
            }
        )
        print(f"sign_up response: {auth_response}")

        if not auth_response.user:
            print("Error: Failed to create auth user")
            print(f"Response: {auth_response}")
            sys.exit(1)

        user_id = auth_response.user.id
        print(f"Created auth user: {user_id}")

        # Update profile to admin role
        # (profile created automatically by trigger)
        client.table("user_profiles").update(
            {
                "role": "admin",
                "display_name": ADMIN_DISPLAY_NAME,
            }
        ).eq("id", user_id).execute()

        print(f"Set role to admin for user: {user_id}")
        print()
        print("=" * 50)
        print("Bootstrap complete!")
        print("=" * 50)
        print(f"Email:    {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")
        print()
        print("You can now login via CLI or API.")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
