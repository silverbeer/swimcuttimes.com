#!/usr/bin/env python3
"""Seed time standards from a parsed image into the database."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from swimcuttimes.parser import TimeStandardParser, convert_sheet_to_time_standards


def get_or_create_event(supabase, stroke: str, distance: int, course: str) -> str:
    """Get event ID, creating if it doesn't exist."""
    # Try to find existing event
    result = (
        supabase.table("events")
        .select("id")
        .eq("stroke", stroke)
        .eq("distance", distance)
        .eq("course", course)
        .execute()
    )

    if result.data:
        return result.data[0]["id"]

    # Create new event
    result = (
        supabase.table("events")
        .insert({"stroke": stroke, "distance": distance, "course": course})
        .execute()
    )
    return result.data[0]["id"]


def seed_time_standards(image_path: str, supabase_url: str, supabase_key: str) -> int:
    """Parse an image and seed its time standards into the database.

    Args:
        image_path: Path to the time standards image
        supabase_url: Supabase project URL
        supabase_key: Supabase anon/service key

    Returns:
        Number of standards inserted
    """
    # Parse the image
    print(f"Parsing image: {image_path}")
    parser = TimeStandardParser()
    sheet = parser.parse_image_file(image_path)
    standards = convert_sheet_to_time_standards(sheet)

    print(f"Parsed {len(standards)} time standards")
    print(f"  Standard: {sheet.standard_name}")
    print(f"  Sanctioning Body: {sheet.sanctioning_body}")
    print(f"  Age Group: {sheet.age_group}")
    print(f"  Year: {sheet.effective_year}")

    # Connect to Supabase
    supabase = create_client(supabase_url, supabase_key)

    # Insert each standard
    inserted = 0
    for ts in standards:
        # Get or create the event
        event_id = get_or_create_event(
            supabase,
            ts.event.stroke.value,
            ts.event.distance,
            ts.event.course.value,
        )

        # Insert the time standard
        data = {
            "event_id": event_id,
            "gender": ts.gender.value,
            "age_group": ts.age_group,
            "standard_name": ts.standard_name,
            "cut_level": ts.cut_level,
            "sanctioning_body": ts.sanctioning_body,
            "time_centiseconds": ts.time_centiseconds,
            "effective_year": ts.effective_year,
        }

        try:
            supabase.table("time_standards").insert(data).execute()
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {ts}: {e}")

    print(f"Inserted {inserted} time standards")
    return inserted


def main():
    """Main entry point."""
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python seed_time_standards.py <image_path>")
        print("  Requires SUPABASE_URL and SUPABASE_KEY environment variables")
        sys.exit(1)

    image_path = sys.argv[1]

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        print("For local development, use:")
        print("  SUPABASE_URL=http://127.0.0.1:54321")
        print("  SUPABASE_KEY=<your-anon-key-from-supabase-status>")
        sys.exit(1)

    seed_time_standards(image_path, supabase_url, supabase_key)


if __name__ == "__main__":
    main()
