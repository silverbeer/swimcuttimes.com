"""Time standard parser using Claude Vision API."""

import base64
import json
from pathlib import Path

import anthropic

from swimcuttimes.models.event import Course, Stroke
from swimcuttimes.models.swimmer import Gender
from swimcuttimes.parser.schemas import ParsedTimeEntry, ParsedTimeStandardSheet

# Mapping for stroke names from various formats
STROKE_MAPPING: dict[str, Stroke] = {
    "free": Stroke.FREESTYLE,
    "freestyle": Stroke.FREESTYLE,
    "back": Stroke.BACKSTROKE,
    "backstroke": Stroke.BACKSTROKE,
    "breast": Stroke.BREASTSTROKE,
    "breaststroke": Stroke.BREASTSTROKE,
    "fly": Stroke.BUTTERFLY,
    "butterfly": Stroke.BUTTERFLY,
    "im": Stroke.IM,
    "individual medley": Stroke.IM,
}

# Mapping for course names
COURSE_MAPPING: dict[str, Course] = {
    "scy": Course.SCY,
    "scm": Course.SCM,
    "lcm": Course.LCM,
}

EXTRACTION_PROMPT = """Analyze this swimming time standards image and extract all the data.

Return a JSON object with this exact structure:
{
  "title": "Full title from the image",
  "sanctioning_body": "Organization name (e.g., 'NE Swimming', 'USA Swimming')",
  "standard_name": "Name of the standard (e.g., 'Silver Championship', 'Futures')",
  "effective_year": 2025,
  "age_group": "Age group if specified (e.g., '15-18') or null if Open/not specified",
  "qualifying_period_start": "Start date if shown or null",
  "qualifying_period_end": "End date if shown or null",
  "entries": [
    {
      "event_distance": 100,
      "event_stroke": "freestyle",
      "course": "scy",
      "gender": "F",
      "time_str": "56.29",
      "cut_level": "Cut Time"
    }
  ]
}

Important:
- Extract ALL time entries from the table
- For gender use "M" for male/boys and "F" for female/girls
- For stroke use lowercase: "freestyle", "backstroke", "breaststroke", "butterfly", "im"
- For course use lowercase: "scy", "scm", "lcm"
- Include both "Cut Time" and "Cut Off Time" entries if present (they are different cut levels)
- Parse times exactly as shown (e.g., "56.29", "1:05.79", "10:29.99")
- If an event shows different distances for different courses (like 400/500 free),
  use the correct distance for each course

Return ONLY the JSON object, no other text."""


class TimeStandardParser:
    """Parser for extracting time standards from images using Claude Vision."""

    def __init__(self, api_key: str | None = None):
        """Initialize the parser.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_image_file(self, image_path: str | Path) -> ParsedTimeStandardSheet:
        """Parse a time standard image from a file path.

        Args:
            image_path: Path to the image file (PNG, JPG, GIF, WEBP)

        Returns:
            ParsedTimeStandardSheet with all extracted data
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Determine media type
        suffix = image_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }

        if suffix not in media_types:
            raise ValueError(f"Unsupported image format: {suffix}")

        media_type = media_types[suffix]

        # Read and encode image
        image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")

        return self._parse_image_data(image_data, media_type)

    def parse_image_bytes(
        self, image_bytes: bytes, media_type: str = "image/png"
    ) -> ParsedTimeStandardSheet:
        """Parse a time standard image from bytes.

        Args:
            image_bytes: Raw image bytes
            media_type: MIME type of the image

        Returns:
            ParsedTimeStandardSheet with all extracted data
        """
        image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
        return self._parse_image_data(image_data, media_type)

    def _parse_image_data(self, image_data: str, media_type: str) -> ParsedTimeStandardSheet:
        """Internal method to parse base64-encoded image data.

        Args:
            image_data: Base64-encoded image data
            media_type: MIME type of the image

        Returns:
            ParsedTimeStandardSheet with all extracted data
        """
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )

        # Extract JSON from response
        response_text = message.content[0].text

        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        try:
            raw_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Show end of response to help debug truncation issues
            raise ValueError(
                f"Failed to parse Claude response as JSON: {e}\n"
                f"Response start: {response_text[:300]}\n"
                f"Response end: {response_text[-300:]}\n"
                f"Stop reason: {message.stop_reason}"
            ) from e

        # Convert to our models
        entries = []
        for entry in raw_data.get("entries", []):
            stroke_key = entry["event_stroke"].lower()
            course_key = entry["course"].lower()

            parsed_entry = ParsedTimeEntry(
                event_distance=entry["event_distance"],
                event_stroke=STROKE_MAPPING.get(stroke_key, Stroke.FREESTYLE),
                course=COURSE_MAPPING.get(course_key, Course.SCY),
                gender=Gender.FEMALE if entry["gender"].upper() == "F" else Gender.MALE,
                time_str=entry["time_str"],
                cut_level=entry["cut_level"],
            )
            entries.append(parsed_entry)

        return ParsedTimeStandardSheet(
            title=raw_data.get("title", ""),
            sanctioning_body=raw_data.get("sanctioning_body", ""),
            standard_name=raw_data.get("standard_name", ""),
            effective_year=raw_data.get("effective_year", 2025),
            age_group=raw_data.get("age_group"),
            qualifying_period_start=raw_data.get("qualifying_period_start"),
            qualifying_period_end=raw_data.get("qualifying_period_end"),
            entries=entries,
        )
