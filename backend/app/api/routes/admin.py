"""Restricted administration entry point."""

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentAdmin, get_current_admin
from app.schemas.admin import AdminIdentityResponse


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/me", response_model=AdminIdentityResponse)
def get_admin_identity(current_admin: CurrentAdmin) -> AdminIdentityResponse:
    """Return a safe identity only after administrator authorization."""
    return AdminIdentityResponse(
        id=current_admin.id,
        email=current_admin.email,
        display_name=current_admin.display_name,
        role=current_admin.role,
    )
