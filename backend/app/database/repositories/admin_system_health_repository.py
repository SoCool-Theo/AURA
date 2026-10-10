"""A transaction-local, read-only probe on the already authorized connection."""

from sqlalchemy import text
from sqlalchemy.orm import Session


class AdminSystemHealthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def database_responds(self) -> bool:
        if self._session.get_bind().dialect.name == "postgresql":
            # Only this request transaction is affected. Closing the caller's
            # session rolls it back; no persistent database setting is changed.
            # Subsequent shared market-status reads use the same per-query bound.
            self._session.execute(text("SET LOCAL statement_timeout = '2000ms'"))
        return self._session.execute(text("SELECT 1")).scalar_one() == 1
