"""Administrator-only identity contract; customer contracts remain unchanged."""

from typing import Literal
from uuid import UUID

from .auth import CanonicalEmail
from .common import AuraBaseModel


class AdminIdentityResponse(AuraBaseModel):
    id: UUID
    email: CanonicalEmail
    display_name: str | None
    role: Literal["ADMIN"]
