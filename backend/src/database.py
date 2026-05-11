import os
from collections.abc import Generator

import bcrypt
from models import Article, Chat, PressReview, User
from sqlalchemy import func
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

_TEST_SQLITE = os.getenv("TEST_SQLITE", "").lower() in ("1", "true", "yes")


def _normalize_database_url(url: str) -> str:
    """Railway / hébergeurs fournissent parfois ``postgres://`` ; SQLAlchemy attend ``postgresql://``."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


_sql_echo = os.getenv("SQL_ECHO", "").lower() in ("1", "true", "yes")

if _TEST_SQLITE:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
else:
    _raw_url = os.getenv("DATABASE_URL") or ""
    DATABASE_URL = _normalize_database_url(_raw_url.strip().strip("'\""))
    engine = create_engine(DATABASE_URL, echo=_sql_echo)


def _seed_password_matches(stored_hash: str | bytes, plain: str) -> bool:
    try:
        stored = (
            stored_hash
            if isinstance(stored_hash, bytes)
            else stored_hash.encode("utf-8")
        )
        return bcrypt.checkpw(plain.encode("utf-8"), stored)
    except ValueError:
        return False


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    print("Database initialized successfully")

    # Tests SQLite : toujours graine pour les tests API. PostgreSQL prod : activer seulement si demandé.
    seed_default = _TEST_SQLITE or os.getenv("SEED_DEFAULT_USER", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not seed_default:
        return

    default_email = "test@test.com"
    default_password = "test"

    with Session(engine) as session:
        statement = select(User).where(
            func.lower(User.email) == default_email.lower(),
        )
        user = session.exec(statement).first()

        if not user:
            hashed = bcrypt.hashpw(
                default_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            session.add(
                User(
                    email=default_email,
                    hashed_password=hashed,
                )
            )
            session.commit()
        elif not _seed_password_matches(user.hashed_password, default_password):
            user.hashed_password = bcrypt.hashpw(
                default_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            session.add(user)
            session.commit()
            session.refresh(user)
