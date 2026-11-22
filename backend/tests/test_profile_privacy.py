"""FR-02: users edit only their own profile; public responses omit private fields."""

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import User
from tests.utils import register

API = "/api/v1"
PRIVATE_FIELDS = {"email", "password_hash", "role", "inference_opt_out", "is_synthetic"}
Clients = Callable[[], TestClient]


def test_fr02_user_edits_own_profile(client: TestClient) -> None:
    register(client, "aru")
    res = client.patch(
        f"{API}/me",
        json={
            "display_name": "  Aru B.  ",
            "bio": "Hiking and chess.",
            "interests": ["Hiking", "chess", "hiking "],
        },
    )
    assert res.status_code == 200
    me = client.get(f"{API}/me").json()
    assert me["display_name"] == "Aru B."
    assert me["bio"] == "Hiking and chess."
    assert me["interests"] == ["chess", "hiking"]  # lower-cased and de-duplicated


def test_fr02_profile_limits_are_enforced(client: TestClient) -> None:
    register(client, "aru")
    too_many = client.patch(f"{API}/me", json={"interests": [f"tag{i}" for i in range(11)]})
    long_bio = client.patch(f"{API}/me", json={"bio": "x" * 281})
    long_tag = client.patch(f"{API}/me", json={"interests": ["x" * 31]})
    assert too_many.status_code == long_bio.status_code == long_tag.status_code == 422


def test_fr02_patch_me_cannot_change_another_user_or_private_fields(
    make_client: Clients, db: Session
) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    dias_before = register(dias, "dias")

    # Extra fields, including someone else's id, are ignored: the target is the session user.
    res = aru.patch(
        f"{API}/me",
        json={"id": dias_before["id"], "username": "dias", "role": "admin", "bio": "mine"},
    )
    assert res.status_code == 200
    assert res.json()["username"] == "aru"
    assert res.json()["role"] == "user"
    assert dias.get(f"{API}/me").json() == dias_before


def test_fr02_public_profile_omits_private_fields(make_client: Clients) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    dias.patch(f"{API}/me", json={"bio": "Runner", "interests": ["running"]})

    profile = aru.get(f"{API}/users/dias").json()
    assert profile["username"] == "dias"
    assert profile["bio"] == "Runner"
    assert profile["interests"] == ["running"]
    assert profile["follower_count"] == 0 and profile["following_count"] == 0
    assert not PRIVATE_FIELDS & set(profile)
    assert "dias@example.com" not in aru.get(f"{API}/users/dias").text


def test_fr02_people_search_omits_private_fields(make_client: Clients) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias", display_name="Dias Nurlan")

    by_username = aru.get(f"{API}/users", params={"query": "dia"}).json()["items"]
    by_name = aru.get(f"{API}/users", params={"query": "NURLAN"}).json()["items"]
    assert [u["username"] for u in by_username] == ["dias"]
    assert [u["username"] for u in by_name] == ["dias"]
    assert not PRIVATE_FIELDS & set(by_username[0])
    # Searching by email finds nothing: email is not a searchable or visible field.
    assert aru.get(f"{API}/users", params={"query": "example.com"}).json()["items"] == []


def test_fr02_deleted_and_unknown_profiles_return_404(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    db.execute(update(User).where(User.username == "dias").values(deleted_at=datetime.now(UTC)))
    db.commit()

    assert aru.get(f"{API}/users/dias").status_code == 404
    assert aru.get(f"{API}/users/nobody").status_code == 404
    assert aru.get(f"{API}/users", params={"query": "dias"}).json()["items"] == []


def test_fr02_profiles_require_sign_in(client: TestClient) -> None:
    assert client.get(f"{API}/users/aru").status_code == 401
    assert client.get(f"{API}/users").status_code == 401
    assert client.patch(f"{API}/me", json={"bio": "x"}).status_code == 401
