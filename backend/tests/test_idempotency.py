"""FR-04: one row, one event, one outbox entry and the same response per Idempotency-Key."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Comment, Follow, InteractionEvent, Like, Outbox, Post
from tests.utils import idem, register

API = "/api/v1"
Clients = Callable[[], TestClient]


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_fr04_same_key_twice_gives_one_post_event_and_outbox_row(
    client: TestClient, db: Session
) -> None:
    register(client, "aru")
    headers = idem()
    first = client.post(f"{API}/posts", json={"body": "Hello"}, headers=headers)
    second = client.post(f"{API}/posts", json={"body": "Hello"}, headers=headers)

    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert count(db, Post) == 1
    assert count(db, InteractionEvent) == 1
    assert count(db, Outbox) == 1


def test_fr04_same_key_with_a_different_body_gives_409(client: TestClient, db: Session) -> None:
    register(client, "aru")
    headers = idem()
    client.post(f"{API}/posts", json={"body": "Hello"}, headers=headers)
    conflict = client.post(f"{API}/posts", json={"body": "Something else"}, headers=headers)

    assert conflict.status_code == 409
    assert conflict.headers["content-type"].startswith("application/problem+json")
    assert count(db, Post) == 1
    assert count(db, InteractionEvent) == 1


def test_fr04_event_and_outbox_are_written_with_the_change(client: TestClient, db: Session) -> None:
    me = register(client, "aru")
    post_id = client.post(f"{API}/posts", json={"body": "Hello"}, headers=idem()).json()["id"]

    event = db.scalars(select(InteractionEvent)).one()
    outbox = db.scalars(select(Outbox)).one()
    assert event.event_type == "post_created"
    assert str(event.actor_id) == me["id"]
    assert str(event.post_id) == post_id
    assert "Hello" not in str(event.payload)  # bodies never enter the event log
    assert outbox.event_id == event.id
    assert outbox.status == "pending"


def test_fr04_follow_like_and_comment_are_idempotent(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    dias_id = register(dias, "dias")["id"]
    post_id = dias.post(f"{API}/posts", json={"body": "Hi"}, headers=idem()).json()["id"]
    before = count(db, InteractionEvent)

    for path, body in (
        (f"{API}/users/{dias_id}/follow", None),
        (f"{API}/posts/{post_id}/like", None),
        (f"{API}/posts/{post_id}/comments", {"body": "Nice"}),
    ):
        headers = idem()
        first = aru.post(path, json=body, headers=headers)
        second = aru.post(path, json=body, headers=headers)
        assert first.status_code == second.status_code == 201, path
        assert first.json() == second.json(), path

    assert count(db, Follow) == count(db, Like) == count(db, Comment) == 1
    assert count(db, InteractionEvent) == before + 3
    assert count(db, Outbox) == before + 3


def test_fr04_key_is_required_and_must_be_a_uuid(client: TestClient, db: Session) -> None:
    register(client, "aru")
    missing = client.post(f"{API}/posts", json={"body": "Hello"})
    malformed = client.post(
        f"{API}/posts", json={"body": "Hello"}, headers={"Idempotency-Key": "abc"}
    )
    assert missing.status_code == malformed.status_code == 400
    assert count(db, Post) == 0


def test_fr04_keys_are_scoped_to_the_user(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    headers = {"Idempotency-Key": str(uuid.uuid4())}

    a = aru.post(f"{API}/posts", json={"body": "From Aru"}, headers=headers)
    d = dias.post(f"{API}/posts", json={"body": "From Dias"}, headers=headers)
    assert a.status_code == d.status_code == 201
    assert a.json()["id"] != d.json()["id"]
    assert count(db, Post) == 2


def test_fr04_failed_request_is_not_stored(client: TestClient, db: Session) -> None:
    register(client, "aru")
    headers = idem()
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.post(f"{API}/posts/{missing}/like", headers=headers).status_code == 404
    assert count(db, InteractionEvent) == 0
    # The key was not consumed, so it still works for a valid request.
    assert client.post(f"{API}/posts", json={"body": "ok"}, headers=headers).status_code == 201
