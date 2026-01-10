# Racing Suit Tracking Feature

## Overview

Add comprehensive racing suit tracking to swimcuttimes.com - a game-changer feature that lets swimmers:
- Track ALL racing suits (tech suits AND regular racing suits)
- Link swim times to specific suits worn
- Analyze performance: tech suit vs regular suit comparisons
- Monitor suit lifespan and know when suits are worn out
- Track purchase details (where bought, price paid)

## Domain Knowledge

**Key Facts from Research:**
- **Tech suits** last **6-12 races at peak performance**, up to 30-40 total
- **Regular racing suits** last much longer (100+ races)
- Major brands: Speedo (LZR Pure Intent), Arena (Carbon Core FX, Primo), TYR (Venzo Genesis)
- Tech suit price range: $200-$500+
- Regular racing suit price range: $30-$100
- Degradation indicators: compression loss, increased water absorption
- Suit types: jammer (men), kneeskin (women), brief
- **High school meets** typically use regular racing suits, not tech suits

Sources: [SwimCompetitive](https://swimcompetitive.com/tech-suits/how-long-do-tech-suits-last/), [SwimOutlet Tech Suit Guide](https://www.swimoutlet.com/blogs/official/elite-tech-suit-review), [YourSwimLog](https://www.yourswimlog.com/tech-suits-guide/)

---

## Data Model

### New Tables

```
suit_models (catalog of ALL racing suit products)
├── id, brand, model_name
├── suit_type (jammer/kneeskin/brief)
├── is_tech_suit (boolean) ← Distinguishes tech vs regular
├── gender, release_year, msrp_cents
├── expected_races_peak (default 10 for tech, 50 for regular)
├── expected_races_total (default 30 for tech, 150 for regular)
└── fina_approved

swimmer_suits (swimmer's inventory)
├── id, swimmer_id, suit_model_id
├── purchase_date, purchase_price_cents
├── purchase_location ← "SwimOutlet", "Dick's", "Team order", etc.
├── wear_count, race_count
├── condition (new/good/worn/retired)
├── nickname, size, color
└── retired_date, retirement_reason

swim_times (existing - add column)
└── suit_id (FK to swimmer_suits, nullable)
```

### Relationships
```
SuitModel (1) ←─── (many) SwimmerSuit (many) ───→ (1) Swimmer
                               │
                               └──── (1) ←─── (many) SwimTime
```

---

## Implementation Steps

### Phase 1: Database Migration
**File:** `supabase/migrations/20260112000000_racing_suits.sql`

1. Create enums: `suit_type`, `suit_condition`
2. Create `suit_models` table (catalog for ALL suits)
3. Create `swimmer_suits` table (inventory)
4. Add `suit_id` column to `swim_times`
5. Add RLS policies (public read, admin/coach write)
6. Add trigger to auto-increment race_count on swim_time insert

### Phase 2: Models
**File:** `backend/src/swimcuttimes/models/suit.py`

```python
class SuitType(StrEnum):
    JAMMER = "jammer"
    KNEESKIN = "kneeskin"
    BRIEF = "brief"

class SuitCondition(StrEnum):
    NEW = "new"
    GOOD = "good"
    WORN = "worn"
    RETIRED = "retired"

class SuitModel(BaseModel):
    # Catalog entry for a suit product
    brand, model_name, suit_type, gender
    is_tech_suit  # True for tech suits, False for regular racing suits
    msrp_cents, expected_races_peak, expected_races_total

class SwimmerSuit(BaseModel):
    # Individual suit in swimmer's inventory
    swimmer_id, suit_model_id
    purchase_date, purchase_price_cents
    purchase_location  # "SwimOutlet", "Dick's", "Team order", etc.
    wear_count, race_count, condition
    nickname, size, color
    # Computed: estimated_remaining_races, life_percentage, is_tech_suit
```

**Update:** `backend/src/swimcuttimes/models/swim_time.py`
- Add `suit_id: UUID | None = None`

### Phase 3: DAOs
**File:** `backend/src/swimcuttimes/dao/suit_dao.py`

```python
class SuitModelDAO(BaseDAO):
    # find_by_brand(), find_by_gender(), search()
    # find_tech_suits(), find_regular_suits()

class SwimmerSuitDAO(BaseDAO):
    # find_by_swimmer(), find_active_by_swimmer()
    # find_tech_suits_by_swimmer(), find_regular_suits_by_swimmer()
    # increment_wear_count(), increment_race_count()
    # retire_suit(), update_condition()
```

**Update:** `swim_time_dao.py` - handle suit_id in _to_model/_to_db

### Phase 4: API Endpoints
**File:** `backend/src/swimcuttimes/api/routes/suits.py`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/suits/models` | user | List/search suit catalog |
| GET | `/suits/models/{id}` | user | Get suit model details |
| POST | `/suits/models` | admin | Add suit to catalog |
| GET | `/suits/inventory?swimmer_id=` | user | List swimmer's suits |
| POST | `/suits/inventory` | coach+ | Add suit to swimmer |
| PATCH | `/suits/inventory/{id}` | coach+ | Update suit details |
| POST | `/suits/inventory/{id}/retire` | coach+ | Retire a suit |

**Analytics endpoints:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/suits/analytics/swimmer/{id}` | user | Overall suit stats |
| GET | `/suits/analytics/compare?swimmer_id=` | user | Tech suit vs regular comparison |

### Phase 5: CLI Commands
**Add to:** `backend/src/swimcuttimes/cli/app.py`

```
suits models [--brand] [--gender] [--tech-only] [--regular-only]
suits model-add <brand> <model> --tech/--regular ...
suits inventory <swimmer> [--tech-only] [--regular-only]
suits add <swimmer> <model_id> [--nickname] [--size] [--price] [--location]
suits retire <suit_id> [--reason]
suits stats <swimmer>                 # Show suit analytics
suits compare <swimmer>               # Tech vs regular comparison
```

### Phase 6: Update SwimTime Recording
- Update `POST /swim-times` to accept optional `suit_id`
- Update `times record` CLI to accept `--suit` option
- Auto-increment suit race_count when time is recorded

### Phase 7: Seed Data
**File:** `supabase/migrations/20260112000001_seed_suits.sql`

Seed common **tech suits**:
- Speedo: LZR Pure Intent, LZR Pure Valor
- Arena: Carbon Core FX, Carbon Glide, Primo
- TYR: Venzo Genesis, Avictor Supernova
- Mizuno: GX Sonic V

Seed common **regular racing suits**:
- Speedo: Endurance+ Jammer, ProLT Jammer
- TYR: Durafast Elite Jammer
- Arena: Solid Jammer, MaxLife
- Speedo: Flyback (women's)

---

## Key Analytics Queries

### Tech Suit vs Regular Suit Comparison
```sql
SELECT e.name as event,
       MIN(CASE WHEN sm.is_tech_suit = true THEN st.time_centiseconds END) AS best_tech,
       MIN(CASE WHEN sm.is_tech_suit = false OR st.suit_id IS NULL THEN st.time_centiseconds END) AS best_regular
FROM swim_times st
LEFT JOIN swimmer_suits ss ON st.suit_id = ss.id
LEFT JOIN suit_models sm ON ss.suit_model_id = sm.id
JOIN events e ON st.event_id = e.id
WHERE st.swimmer_id = ?
GROUP BY e.id, e.name
```

### Suit Lifespan Tracking
```sql
SELECT ss.nickname, ss.race_count, sm.expected_races_total,
       ROUND(ss.race_count::numeric / sm.expected_races_total * 100) AS life_used_pct,
       CASE WHEN ss.race_count >= sm.expected_races_peak THEN 'Past Peak' ELSE 'Good' END AS status,
       sm.is_tech_suit
FROM swimmer_suits ss
JOIN suit_models sm ON ss.suit_model_id = sm.id
WHERE ss.swimmer_id = ? AND ss.condition != 'retired'
ORDER BY life_used_pct DESC
```

### Best Suit by Event Type
Group by sprint (50-100), middle (200-400), distance (500+) and show which suit produced most PBs.

---

## Files to Create/Modify

### New Files
- `supabase/migrations/20260112000000_racing_suits.sql`
- `supabase/migrations/20260112000001_seed_suits.sql`
- `backend/src/swimcuttimes/models/suit.py`
- `backend/src/swimcuttimes/dao/suit_dao.py`
- `backend/src/swimcuttimes/api/routes/suits.py`
- `backend/tests/api/test_suits.py`

### Modified Files
- `backend/src/swimcuttimes/models/__init__.py` - export new models
- `backend/src/swimcuttimes/models/swim_time.py` - add suit_id
- `backend/src/swimcuttimes/dao/swim_time_dao.py` - handle suit_id
- `backend/src/swimcuttimes/api/dependencies.py` - add new DAOs
- `backend/src/swimcuttimes/api/routes/__init__.py` - register router
- `backend/src/swimcuttimes/api/app.py` - include router
- `backend/src/swimcuttimes/api/routes/swim_times.py` - accept suit_id
- `backend/src/swimcuttimes/cli/app.py` - add suits commands

---

## Verification Plan

### Database
```bash
./scripts/db.sh migrate
./scripts/db.sh status
```

### API Testing
```bash
cd backend
uv run pytest tests/api/test_suits.py -v
```

### End-to-End CLI Test
```bash
# 1. List suit catalog
uv run swimcuttimes suits models

# 2. Add suit to swimmer's inventory
uv run swimcuttimes suits add "Jane Doe" <model_id> --nickname "Lucky Suit" --size 26

# 3. View inventory
uv run swimcuttimes suits inventory "Jane Doe"

# 4. Record time with suit
uv run swimcuttimes times record --swimmer "Jane Doe" --meet "Championships" \
    --event "100 free scy" --time "58.45" --suit <suit_id>

# 5. Check suit stats
uv run swimcuttimes suits stats "Jane Doe"

# 6. Retire worn suit
uv run swimcuttimes suits retire <suit_id> --reason "Lost compression"
```

---

## Future Enhancements

1. **Photo tracking** - Upload suit photos for visual ID
2. **Fit tracking** - Rate compression feel over time (1-5 scale after each race)
3. **Cost analysis** - Cost per race, ROI calculations
4. **Team coordination** - Track team suit orders/inventory
5. **Recommendations** - Suggest suits based on event profile and body type
6. **Marketplace** - Buy/sell used suits in community
7. **Comparison tool** - Side-by-side suit specs comparison
