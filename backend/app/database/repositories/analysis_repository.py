"""Persistence operations for immutable Aura analysis snapshots."""

from copy import deepcopy
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Analysis


class AnalysisRepository:
    """Persist analysis snapshots within a caller-owned session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_snapshot(
        self,
        *,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
        schema_version: str,
        result_snapshot: dict[str, Any],
    ) -> Analysis:
        """Add an independent snapshot copy without committing."""
        analysis = Analysis(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
            schema_version=schema_version,
            result_snapshot=deepcopy(result_snapshot),
        )
        self._session.add(analysis)
        self._session.flush()
        return analysis

    def get_by_id(self, analysis_id: UUID) -> Analysis | None:
        """Return an analysis by primary key, or ``None`` when absent."""
        return self._session.get(Analysis, analysis_id)

    def list_for_portfolio(self, portfolio_id: UUID) -> list[Analysis]:
        """Return a portfolio's newest analyses in deterministic order."""
        statement = (
            select(Analysis)
            .where(Analysis.portfolio_id == portfolio_id)
            .order_by(Analysis.created_at.desc(), Analysis.id)
        )
        return list(self._session.scalars(statement).all())
