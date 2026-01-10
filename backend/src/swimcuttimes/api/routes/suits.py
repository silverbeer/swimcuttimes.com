"""Racing Suit API endpoints.

All endpoints require authentication (invite-only app).
Suit catalog: Admin only for create/update/delete.
Swimmer suits: Admin/coach for create/update/delete, users can read.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminOrCoachUser, AdminUser, CurrentUser
from swimcuttimes.api.dependencies import (
    SuitModelDAODep,
    SwimmerDAODep,
    SwimmerSuitDAODep,
)
from swimcuttimes.models import Gender
from swimcuttimes.models.suit import SuitCondition, SuitModel, SuitType, SwimmerSuit

logger = get_logger(__name__)

router = APIRouter(prefix="/suits", tags=["suits"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class SuitModelCreate(BaseModel):
    """Request body for creating a suit model."""

    brand: str
    model_name: str
    suit_type: SuitType
    is_tech_suit: bool = False
    gender: Gender
    release_year: int | None = None
    msrp_cents: int | None = None
    expected_races_peak: int = Field(default=10, ge=1)
    expected_races_total: int = Field(default=30, ge=1)
    fina_approved: bool = True
    notes: str | None = None


class SuitModelUpdate(BaseModel):
    """Request body for updating a suit model (partial)."""

    brand: str | None = None
    model_name: str | None = None
    suit_type: SuitType | None = None
    is_tech_suit: bool | None = None
    gender: Gender | None = None
    release_year: int | None = None
    msrp_cents: int | None = None
    expected_races_peak: int | None = None
    expected_races_total: int | None = None
    fina_approved: bool | None = None
    notes: str | None = None


class SuitModelResponse(BaseModel):
    """Response model for suit model."""

    id: UUID
    brand: str
    model_name: str
    suit_type: SuitType
    is_tech_suit: bool
    gender: Gender
    release_year: int | None
    msrp_cents: int | None
    msrp_formatted: str | None
    expected_races_peak: int
    expected_races_total: int
    fina_approved: bool
    suit_category: str
    notes: str | None

    @classmethod
    def from_model(cls, model: SuitModel) -> "SuitModelResponse":
        return cls(
            id=model.id,
            brand=model.brand,
            model_name=model.model_name,
            suit_type=model.suit_type,
            is_tech_suit=model.is_tech_suit,
            gender=model.gender,
            release_year=model.release_year,
            msrp_cents=model.msrp_cents,
            msrp_formatted=model.msrp_formatted,
            expected_races_peak=model.expected_races_peak,
            expected_races_total=model.expected_races_total,
            fina_approved=model.fina_approved,
            suit_category=model.suit_category,
            notes=model.notes,
        )


class SwimmerSuitCreate(BaseModel):
    """Request body for adding a suit to swimmer's inventory."""

    swimmer_id: UUID
    suit_model_id: UUID
    nickname: str | None = None
    size: str | None = None
    color: str | None = None
    purchase_date: date | None = None
    purchase_price_cents: int | None = None
    purchase_location: str | None = None


class SwimmerSuitUpdate(BaseModel):
    """Request body for updating a swimmer suit (partial)."""

    nickname: str | None = None
    size: str | None = None
    color: str | None = None
    purchase_date: date | None = None
    purchase_price_cents: int | None = None
    purchase_location: str | None = None
    condition: SuitCondition | None = None


class SwimmerSuitResponse(BaseModel):
    """Response model for swimmer suit."""

    id: UUID
    swimmer_id: UUID
    suit_model_id: UUID
    nickname: str | None
    size: str | None
    color: str | None
    purchase_date: date | None
    purchase_price_cents: int | None
    purchase_price_formatted: str | None
    purchase_location: str | None
    wear_count: int
    race_count: int
    condition: SuitCondition
    is_current: bool
    retired_date: date | None
    retirement_reason: str | None

    @classmethod
    def from_model(cls, model: SwimmerSuit) -> "SwimmerSuitResponse":
        return cls(
            id=model.id,
            swimmer_id=model.swimmer_id,
            suit_model_id=model.suit_model_id,
            nickname=model.nickname,
            size=model.size,
            color=model.color,
            purchase_date=model.purchase_date,
            purchase_price_cents=model.purchase_price_cents,
            purchase_price_formatted=model.purchase_price_formatted,
            purchase_location=model.purchase_location,
            wear_count=model.wear_count,
            race_count=model.race_count,
            condition=model.condition,
            is_current=model.is_current,
            retired_date=model.retired_date,
            retirement_reason=model.retirement_reason,
        )


class SwimmerSuitWithModel(SwimmerSuitResponse):
    """Response with suit model details included."""

    suit_model: SuitModelResponse | None = None
    life_percentage: float | None = None
    remaining_races: int | None = None
    is_past_peak: bool | None = None


class RetireSuitRequest(BaseModel):
    """Request body for retiring a suit."""

    retirement_reason: str | None = None
    retired_date: date = Field(default_factory=date.today)


# =============================================================================
# SUIT MODELS (Catalog)
# =============================================================================


@router.get("/models", response_model=list[SuitModelResponse])
def list_suit_models(
    user: CurrentUser,
    dao: SuitModelDAODep,
    brand: str | None = Query(None, description="Filter by brand"),
    model_name: str | None = Query(None, description="Search model name"),
    suit_type: SuitType | None = Query(None, description="Filter by suit type"),
    is_tech_suit: bool | None = Query(None, description="Filter tech suits vs regular"),
    gender: Gender | None = Query(None, description="Filter by gender"),
    fina_approved: bool | None = Query(None, description="Filter by FINA approval"),
    limit: int = Query(100, ge=1, le=500),
) -> list[SuitModelResponse]:
    """List suit models (catalog) with optional filters."""
    models = dao.search(
        brand=brand,
        model_name=model_name,
        suit_type=suit_type,
        is_tech_suit=is_tech_suit,
        gender=gender,
        fina_approved=fina_approved,
        limit=limit,
    )
    return [SuitModelResponse.from_model(m) for m in models]


@router.get("/models/{model_id}", response_model=SuitModelResponse)
def get_suit_model(
    model_id: UUID,
    user: CurrentUser,
    dao: SuitModelDAODep,
) -> SuitModelResponse:
    """Get a specific suit model by ID."""
    result = dao.get_by_id(model_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit model not found")
    return SuitModelResponse.from_model(result)


@router.post("/models", response_model=SuitModelResponse, status_code=status.HTTP_201_CREATED)
def create_suit_model(
    data: SuitModelCreate,
    user: AdminUser,
    dao: SuitModelDAODep,
) -> SuitModelResponse:
    """Create a new suit model (admin only)."""
    try:
        model = SuitModel(
            brand=data.brand,
            model_name=data.model_name,
            suit_type=data.suit_type,
            is_tech_suit=data.is_tech_suit,
            gender=data.gender,
            release_year=data.release_year,
            msrp_cents=data.msrp_cents,
            expected_races_peak=data.expected_races_peak,
            expected_races_total=data.expected_races_total,
            fina_approved=data.fina_approved,
            notes=data.notes,
        )
        result = dao.create(model)

        logger.info(
            "suit_model_created",
            suit_model_id=str(result.id),
            brand=data.brand,
            model_name=data.model_name,
        )
        return SuitModelResponse.from_model(result)

    except Exception as e:
        logger.error("suit_model_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create suit model: {e}",
        ) from e


@router.patch("/models/{model_id}", response_model=SuitModelResponse)
def update_suit_model(
    model_id: UUID,
    data: SuitModelUpdate,
    user: AdminUser,
    dao: SuitModelDAODep,
) -> SuitModelResponse:
    """Update a suit model (admin only)."""
    existing = dao.get_by_id(model_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit model not found")

    try:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return SuitModelResponse.from_model(existing)

        # Convert enums to values for the update
        if "suit_type" in updates and isinstance(updates["suit_type"], SuitType):
            updates["suit_type"] = updates["suit_type"].value
        if "gender" in updates and isinstance(updates["gender"], Gender):
            updates["gender"] = updates["gender"].value

        result = dao.table.update(updates).eq("id", str(model_id)).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Suit model not found"
            )

        updated = dao.get_by_id(model_id)
        logger.info(
            "suit_model_updated",
            suit_model_id=str(model_id),
            updated_fields=list(updates.keys()),
        )
        return SuitModelResponse.from_model(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("suit_model_update_error", suit_model_id=str(model_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update suit model: {e}",
        ) from e


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_suit_model(
    model_id: UUID,
    user: AdminUser,
    dao: SuitModelDAODep,
) -> None:
    """Delete a suit model (admin only)."""
    existing = dao.get_by_id(model_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit model not found")

    try:
        deleted = dao.delete(model_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Suit model not found"
            )

        logger.info(
            "suit_model_deleted",
            suit_model_id=str(model_id),
            brand=existing.brand,
            model_name=existing.model_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("suit_model_delete_error", suit_model_id=str(model_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete suit model: {e}",
        ) from e


# =============================================================================
# SWIMMER SUITS (Inventory)
# =============================================================================


@router.get("/inventory", response_model=list[SwimmerSuitWithModel])
def list_swimmer_suits(
    user: CurrentUser,
    suit_dao: SwimmerSuitDAODep,
    model_dao: SuitModelDAODep,
    swimmer_id: UUID = Query(..., description="Swimmer ID (required)"),
    active_only: bool = Query(True, description="Only show non-retired suits"),
) -> list[SwimmerSuitWithModel]:
    """List suits in a swimmer's inventory."""
    if active_only:
        suits = suit_dao.find_active_by_swimmer(swimmer_id)
    else:
        suits = suit_dao.find_by_swimmer(swimmer_id)

    responses = []
    for suit in suits:
        model = model_dao.get_by_id(suit.suit_model_id)
        response = SwimmerSuitWithModel(
            id=suit.id,
            swimmer_id=suit.swimmer_id,
            suit_model_id=suit.suit_model_id,
            nickname=suit.nickname,
            size=suit.size,
            color=suit.color,
            purchase_date=suit.purchase_date,
            purchase_price_cents=suit.purchase_price_cents,
            purchase_price_formatted=suit.purchase_price_formatted,
            purchase_location=suit.purchase_location,
            wear_count=suit.wear_count,
            race_count=suit.race_count,
            condition=suit.condition,
            is_current=suit.is_current,
            retired_date=suit.retired_date,
            retirement_reason=suit.retirement_reason,
            suit_model=SuitModelResponse.from_model(model) if model else None,
            life_percentage=suit.life_percentage(model.expected_races_total) if model else None,
            remaining_races=suit.remaining_races(model.expected_races_total) if model else None,
            is_past_peak=suit.is_past_peak(model.expected_races_peak) if model else None,
        )
        responses.append(response)

    return responses


@router.get("/inventory/{suit_id}", response_model=SwimmerSuitWithModel)
def get_swimmer_suit(
    suit_id: UUID,
    user: CurrentUser,
    suit_dao: SwimmerSuitDAODep,
    model_dao: SuitModelDAODep,
) -> SwimmerSuitWithModel:
    """Get a specific swimmer suit by ID."""
    suit = suit_dao.get_by_id(suit_id)
    if not suit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit not found")

    model = model_dao.get_by_id(suit.suit_model_id)

    return SwimmerSuitWithModel(
        id=suit.id,
        swimmer_id=suit.swimmer_id,
        suit_model_id=suit.suit_model_id,
        nickname=suit.nickname,
        size=suit.size,
        color=suit.color,
        purchase_date=suit.purchase_date,
        purchase_price_cents=suit.purchase_price_cents,
        purchase_price_formatted=suit.purchase_price_formatted,
        purchase_location=suit.purchase_location,
        wear_count=suit.wear_count,
        race_count=suit.race_count,
        condition=suit.condition,
        is_current=suit.is_current,
        retired_date=suit.retired_date,
        retirement_reason=suit.retirement_reason,
        suit_model=SuitModelResponse.from_model(model) if model else None,
        life_percentage=suit.life_percentage(model.expected_races_total) if model else None,
        remaining_races=suit.remaining_races(model.expected_races_total) if model else None,
        is_past_peak=suit.is_past_peak(model.expected_races_peak) if model else None,
    )


@router.post("/inventory", response_model=SwimmerSuitResponse, status_code=status.HTTP_201_CREATED)
def create_swimmer_suit(
    data: SwimmerSuitCreate,
    user: AdminOrCoachUser,
    suit_dao: SwimmerSuitDAODep,
    model_dao: SuitModelDAODep,
    swimmer_dao: SwimmerDAODep,
) -> SwimmerSuitResponse:
    """Add a suit to a swimmer's inventory (admin or coach only)."""
    # Verify swimmer exists
    swimmer = swimmer_dao.get_by_id(data.swimmer_id)
    if not swimmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    # Verify suit model exists
    model = model_dao.get_by_id(data.suit_model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit model not found")

    try:
        suit = SwimmerSuit(
            swimmer_id=data.swimmer_id,
            suit_model_id=data.suit_model_id,
            nickname=data.nickname,
            size=data.size,
            color=data.color,
            purchase_date=data.purchase_date,
            purchase_price_cents=data.purchase_price_cents,
            purchase_location=data.purchase_location,
        )
        result = suit_dao.create(suit)

        logger.info(
            "swimmer_suit_created",
            suit_id=str(result.id),
            swimmer_id=str(data.swimmer_id),
            suit_model=f"{model.brand} {model.model_name}",
        )
        return SwimmerSuitResponse.from_model(result)

    except Exception as e:
        logger.error("swimmer_suit_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add suit: {e}",
        ) from e


@router.patch("/inventory/{suit_id}", response_model=SwimmerSuitResponse)
def update_swimmer_suit(
    suit_id: UUID,
    data: SwimmerSuitUpdate,
    user: AdminOrCoachUser,
    suit_dao: SwimmerSuitDAODep,
) -> SwimmerSuitResponse:
    """Update a swimmer's suit (admin or coach only)."""
    existing = suit_dao.get_by_id(suit_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit not found")

    try:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return SwimmerSuitResponse.from_model(existing)

        result = suit_dao.partial_update(suit_id, updates)

        logger.info(
            "swimmer_suit_updated",
            suit_id=str(suit_id),
            updated_fields=list(updates.keys()),
        )
        return SwimmerSuitResponse.from_model(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swimmer_suit_update_error", suit_id=str(suit_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update suit: {e}",
        ) from e


@router.post("/inventory/{suit_id}/retire", response_model=SwimmerSuitResponse)
def retire_swimmer_suit(
    suit_id: UUID,
    data: RetireSuitRequest,
    user: AdminOrCoachUser,
    suit_dao: SwimmerSuitDAODep,
) -> SwimmerSuitResponse:
    """Retire a swimmer's suit (admin or coach only)."""
    existing = suit_dao.get_by_id(suit_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit not found")

    if existing.condition == SuitCondition.RETIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Suit is already retired"
        )

    try:
        result = suit_dao.retire_suit(suit_id, data.retirement_reason, data.retired_date)

        logger.info(
            "swimmer_suit_retired",
            suit_id=str(suit_id),
            swimmer_id=str(existing.swimmer_id),
            reason=data.retirement_reason,
        )
        return SwimmerSuitResponse.from_model(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swimmer_suit_retire_error", suit_id=str(suit_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retire suit: {e}",
        ) from e


@router.delete("/inventory/{suit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_swimmer_suit(
    suit_id: UUID,
    user: AdminUser,
    suit_dao: SwimmerSuitDAODep,
) -> None:
    """Delete a swimmer's suit (admin only)."""
    existing = suit_dao.get_by_id(suit_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit not found")

    try:
        deleted = suit_dao.delete(suit_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suit not found")

        logger.info(
            "swimmer_suit_deleted",
            suit_id=str(suit_id),
            swimmer_id=str(existing.swimmer_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swimmer_suit_delete_error", suit_id=str(suit_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete suit: {e}",
        ) from e
