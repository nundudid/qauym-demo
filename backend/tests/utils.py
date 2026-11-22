import uuid
from typing import Any

from fastapi.testclient import TestClient

PASSWORD = "correct-horse-battery"


def register(client: TestClient, username: str, **extra: Any) -> dict[str, Any]:
    """Register through the API; the client keeps the session cookie."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": PASSWORD,
            **extra,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def idem() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}
