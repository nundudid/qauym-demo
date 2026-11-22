"""FR-01 and NFR-03: accounts, sessions, password storage and rate limiting."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Session as UserSession
from app.models import User
from app.security import hash_token
from tests.utils import PASSWORD, register

API = "/api/v1"
COOKIE = "qauym_session"


def test_fr01_register_creates_account_and_signs_in(client: TestClient) -> None:
    body = register(client, "aru", display_name="Aru")
    assert body["username"] == "aru"
    assert body["display_name"] == "Aru"
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body
    assert client.get(f"{API}/me").json()["email"] == "aru@example.com"


def test_fr01_session_cookie_is_httponly_and_samesite_lax(client: TestClient) -> None:
    res = client.post(
        f"{API}/auth/register",
        json={"email": "aru@example.com", "username": "aru", "password": PASSWORD},
    )
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=1209600" in cookie  # 14 days


def test_fr01_duplicate_account_rejected(
    client: TestClient, make_client: Callable[[], TestClient], db: Session
) -> None:
    register(client, "aru")
    other = make_client()
    same_email = other.post(
        f"{API}/auth/register",
        json={"email": "ARU@example.com", "username": "someone_else", "password": PASSWORD},
    )
    same_username = other.post(
        f"{API}/auth/register",
        json={"email": "new@example.com", "username": "Aru", "password": PASSWORD},
    )
    assert same_email.status_code == 409
    assert same_username.status_code == 409
    assert same_email.json()["detail"] == same_username.json()["detail"]
    assert len(db.scalars(select(User)).all()) == 1


def test_fr01_wrong_password_and_unknown_email_give_the_same_generic_error(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, "aru")
    other = make_client()
    wrong = other.post(
        f"{API}/auth/login", json={"email": "aru@example.com", "password": "not-the-password"}
    )
    unknown = other.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.headers["content-type"].startswith("application/problem+json")
    assert set(wrong.json()) == {"type", "title", "status", "detail"}
    assert COOKIE not in other.cookies


def test_fr01_requests_after_logout_get_401(client: TestClient) -> None:
    register(client, "aru")
    token = client.cookies[COOKIE]
    assert client.post(f"{API}/auth/logout").status_code == 204
    assert client.get(f"{API}/me").status_code == 401

    # Replaying the old cookie must fail too: the session is revoked on the server.
    client.cookies.set(COOKIE, token)
    assert client.get(f"{API}/me").status_code == 401


def test_fr01_login_rotates_the_session_token(client: TestClient, db: Session) -> None:
    register(client, "aru")
    old = client.cookies[COOKIE]
    res = client.post(f"{API}/auth/login", json={"email": "aru@example.com", "password": PASSWORD})
    assert res.status_code == 200
    new = client.cookies[COOKIE]
    assert new != old
    old_row = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(old)))
    assert old_row is not None and old_row.revoked_at is not None


def test_nfr03_password_is_argon2id_and_token_is_stored_hashed(
    client: TestClient, db: Session
) -> None:
    register(client, "aru")
    user = db.scalars(select(User)).one()
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash
    token = client.cookies[COOKIE]
    session = db.scalars(select(UserSession)).one()
    assert session.token_hash == hash_token(token) != token


def test_nfr03_unauthenticated_requests_get_401(client: TestClient) -> None:
    assert client.get(f"{API}/me").status_code == 401
    assert client.post(f"{API}/auth/logout").status_code == 401


def test_nfr03_mutations_require_the_client_header_and_json(
    make_client: Callable[[], TestClient],
) -> None:
    c = make_client()
    payload = {"email": "aru@example.com", "username": "aru", "password": PASSWORD}
    no_header = c.post(f"{API}/auth/register", json=payload, headers={"X-Qauym-Client": ""})
    assert no_header.status_code == 403
    form = c.post(f"{API}/auth/register", data=payload)
    assert form.status_code == 415


def test_fr01_validation_errors_do_not_echo_the_password(client: TestClient) -> None:
    res = client.post(
        f"{API}/auth/register",
        json={"email": "not-an-email", "username": "x", "password": "short12"},
    )
    assert res.status_code == 422
    assert "short12" not in res.text
    assert {e["field"] for e in res.json()["errors"]} == {"email", "username", "password"}


def test_nfr03_login_is_rate_limited_per_ip(client: TestClient) -> None:
    body = {"email": "nobody@example.com", "password": "whatever-123"}
    statuses = [client.post(f"{API}/auth/login", json=body).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
