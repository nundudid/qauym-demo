from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app


def test_health_reports_database_ok(client: TestClient) -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(client: TestClient) -> None:
    class BrokenSession:
        def execute(self, *_: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("down"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        res = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 503
    assert res.json()["database"] == "unavailable"


def test_openapi_schema_is_served_under_api_prefix(client: TestClient) -> None:
    assert client.get("/api/v1/openapi.json").status_code == 200
