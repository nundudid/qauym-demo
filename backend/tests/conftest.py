import os

# Tests always run against the separate test database, never the app database.
# This must happen before anything imports app.db.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://qauym:qauym@localhost:5432/qauym_test"
)

# Rate-limit counters go to a separate Valkey database that tests may flush.
os.environ["VALKEY_URL"] = (
    os.environ.get("VALKEY_URL", "redis://localhost:6379/0").rsplit("/", 1)[0] + "/15"
)

from collections.abc import Callable, Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.rate_limit import get_valkey  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def alembic_cfg() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_database(alembic_cfg: Config) -> None:
    """Start every test session from an empty database migrated to head."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    get_valkey().flushdb()
    yield
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def make_client() -> Iterator[Callable[[], TestClient]]:
    """Each client has its own cookie jar, so each one is a separate browser."""
    clients: list[TestClient] = []

    def factory() -> TestClient:
        c = TestClient(app, headers={"X-Qauym-Client": "web"})
        clients.append(c)
        return c

    yield factory
    for c in clients:
        c.close()


@pytest.fixture
def client(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()
