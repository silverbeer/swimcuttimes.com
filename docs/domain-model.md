# Domain Model

## Overview

The application supports **multiple users/swimmers** with complex team relationships. Swimmers can belong to multiple teams simultaneously and change teams over time.

## Entities

### User
App user authenticated via Supabase Auth. A user may optionally be linked to a Swimmer profile.

### Swimmer
A person who swims competitively. Core attributes:
- Name, date of birth, gender
- Optional link to User account
- Historical team affiliations

### Team
A swimming organization. Types:
- `club` - Year-round swim club (e.g., YMCA, private clubs)
- `high_school` - High school team
- `college` - College/university team
- `national` - National team
- `olympic` - Olympic team

**Team fields:**
- `name` - Team name
- `team_type` - One of the types above
- `sanctioning_body` - Primary sanctioning body (e.g., "USA Swimming", "NCAA", "FINA")
- `lsc` - LSC code for club teams (e.g., "NE", "PV") - null for non-club
- `division` - For college teams (e.g., "D1", "D2", "D3", "NAIA") - null for non-college
- `state` - State/region for high school teams
- `country` - Country code (for national/olympic teams)

This allows team-level context while keeping TimeStandard simple.

### SwimmerTeam (Join Table)
Many-to-many relationship between Swimmer and Team with temporal data:
- `swimmer_id` - FK to Swimmer
- `team_id` - FK to Team
- `start_date` - When swimmer joined team
- `end_date` - When swimmer left team (null if current)
- `team_type` - Type of affiliation

This design supports:
- Swimmers on multiple teams simultaneously (club + high school)
- Historical tracking of team changes
- Querying "who was on team X during season Y"

### Event
A swimming event defined by:
- `stroke` - freestyle, backstroke, breaststroke, butterfly, IM
- `distance` - 25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650
- `course` - SCY, SCM, LCM

**Event equivalents across courses:**
| SCY | SCM/LCM |
|-----|---------|
| 500 free | 400 free |
| 1000 free | 800 free |
| 1650 free | 1500 free |

These equivalents matter when comparing times or displaying standards side-by-side (as in the Silver Championship image).

### TimeStandard
Cut times for qualification, defined by:
- `event_id` - FK to Event
- `course` - SCY, SCM, or LCM
- `gender` - M or F
- `age_group` - e.g., "10U", "11-12", "13-14", "15-18", "Open", or null
- `standard_name` - Name of the standard (e.g., "Silver Championship", "Futures", "NCAA D1")
- `cut_level` - Level within the standard (e.g., "Cut Time", "Cut Off Time", "A", "AA")
- `time` - The qualifying time (stored as centiseconds)
- `sanctioning_body` - Organization that defines this standard (e.g., "NE Swimming", "NCAA D1", "USA Swimming")
- `qualifying_start` - Start of qualifying period
- `qualifying_end` - End of qualifying period (null if ongoing)
- `effective_year` - Year the standard applies to (e.g., 2025)

**Age group handling:**
- `"Open"` or `null` = No age restriction. If you hit the time, you qualify regardless of age.
- Examples: Seniors Championship, USA Swimming Futures/Juniors/Nationals, NCAA
- A 10-year-old with a Futures cut qualifies for Futures

Age-group specific standards (like Silver Championship 15-18) use specific values like `"15-18"`.

### Meet
A swim meet/competition:
- `name` - Meet name (e.g., "2025 NE Silver Championship")
- `location` - Venue name
- `city`, `state`, `country` - Location details
- `start_date`, `end_date` - Meet dates
- `course` - SCY, SCM, or LCM
- `lanes` - Number of lanes in the pool (6, 8, 10)
- `indoor` - Boolean (true = indoor, false = outdoor)
- `sanctioning_body` - Who sanctioned the meet
- `meet_type` - e.g., "championship", "invitational", "dual", "time_trial"

### SwimTime
A swimmer's recorded time:
- `swimmer_id` - FK to Swimmer
- `event_id` - FK to Event
- `meet_id` - FK to Meet
- `time` - The time (stored as centiseconds for precision)
- `date` - Date of the swim
- `team_id` - Team swimmer represented at time of swim
- `round` - "prelims", "finals", "consolation", "bonus_finals", "time_trial", or null
- `lane` - Lane number (optional, 1-10)
- `place` - Finish place in heat/final (optional)
- `official` - Boolean (official/unofficial)
- `dq` - Boolean (disqualified)
- `dq_reason` - Reason for DQ if applicable

**Round tracking:**
- Prelims → Finals progression shows improvement or consistency
- "What place did I need in prelims to make finals?" becomes answerable
- Consolation finals (places 9-16) tracked separately from championship finals (1-8)

## Sanctioning Bodies

The `sanctioning_body` field identifies who defines the time standard:

| Audience | sanctioning_body examples | Notes |
|----------|---------------------------|-------|
| **Club** | "NE Swimming", "PV Swimming" | LSC-specific standards |
| **Club (National)** | "USA Swimming" | National-level (Futures, Juniors, Nationals) |
| **High School** | "MIAA", "CIAC" | State athletic associations |
| **College** | "NCAA D1", "NCAA D2", "NCAA D3", "NAIA" | Division-specific |
| **International** | "FINA", "World Aquatics" | Olympic/World Championship qualifying |

**Target audience**: Club, high school, and college swimmers (primary). Olympic-level supported.

## Key Queries

The data model supports these common queries:
1. What times does swimmer X need to achieve standard Y?
2. Which swimmers on team X have achieved standard Y?
3. What was swimmer X's progression over time?
4. Who are the fastest swimmers in event Y for age group Z?
5. What teams has swimmer X been affiliated with?
6. How did swimmer X perform in prelims vs finals?
7. What's the typical prelim-to-finals improvement for event Y?
8. How do times differ at indoor vs outdoor meets?
9. What lane was swimmer X in when they set their PR?
