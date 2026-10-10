"""Explicit operator command; imports, help, and missing --apply never write."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.services.admin_access_service import AdminAccessService, AdminBootstrapError


def bootstrap_admin(user_id: UUID) -> None:
    engine = create_database_engine()
    try:
        with session_scope(create_session_factory(engine)) as session:
            AdminAccessService(session).bootstrap_first_admin(user_id)
            session.commit()
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Promote Aura's first administrator.")
    parser.add_argument("--user-id", type=UUID, required=True)
    parser.add_argument(
        "--apply", action="store_true", help="Explicitly authorize the role change."
    )
    args = parser.parse_args(argv)
    if not args.apply:
        parser.error("--apply is required to authorize the role change")
    try:
        bootstrap_admin(args.user_id)
    except AdminBootstrapError as error:
        raise SystemExit(str(error)) from error
    except (SQLAlchemyError, RuntimeError, ValueError) as error:
        raise SystemExit(
            "Administrator bootstrap failed; check database configuration and migrations."
        ) from error
    print("First administrator provisioned.")


if __name__ == "__main__":
    main()
