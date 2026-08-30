"""Overview endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.overview import compute_overview
from app.domain.schemas import OverviewOut

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewOut)
def overview(db: Session = Depends(get_db)) -> dict:
    return compute_overview(db)
