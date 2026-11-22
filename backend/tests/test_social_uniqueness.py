"""FR-03: posts, feed, follows, likes and comments; uniqueness and ownership."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Comment, Follow, InteractionEvent, Like, Post
from tests.utils import idem, register

API = "/api/v1"
Clients = Callable[[], TestClient]


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def events(db: Session, event_type: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(InteractionEvent)
            .where(InteractionEvent.event_type == event_type)
        )
        or 0
    )


def post(client: TestClient, body: str) -> dict:
    res = client.post(f"{API}/posts", json={"body": body}, headers=idem())
    assert res.status_code == 201, res.text
    return res.json()


def test_fr03_double_follow_creates_one_row(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    dias_id = register(dias, "dias")["id"]

    first = aru.post(f"{API}/users/{dias_id}/follow", headers=idem())
    second = aru.post(f"{API}/users/{dias_id}/follow", headers=idem())  # a different key
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json() == second.json() == {"following": True}
    assert count(db, Follow) == 1
    assert events(db, "followed") == 1

    profile = aru.get(f"{API}/users/dias").json()
    assert profile["follower_count"] == 1 and profile["is_following"] is True


def test_fr03_unfollow_removes_the_row_once(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    dias_id = register(dias, "dias")["id"]
    aru.post(f"{API}/users/{dias_id}/follow", headers=idem())

    assert aru.delete(f"{API}/users/{dias_id}/follow").json() == {"following": False}
    assert aru.delete(f"{API}/users/{dias_id}/follow").status_code == 200
    assert count(db, Follow) == 0
    assert events(db, "unfollowed") == 1


def test_fr03_cannot_follow_yourself_or_a_missing_user(client: TestClient, db: Session) -> None:
    me = register(client, "aru")
    assert client.post(f"{API}/users/{me['id']}/follow", headers=idem()).status_code == 422
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.post(f"{API}/users/{missing}/follow", headers=idem()).status_code == 404
    assert count(db, Follow) == 0


def test_fr03_double_like_creates_one_row(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    post_id = post(dias, "Hello from Dias")["id"]

    first = aru.post(f"{API}/posts/{post_id}/like", headers=idem())
    second = aru.post(f"{API}/posts/{post_id}/like", headers=idem())
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == {"liked": True, "like_count": 1}
    assert count(db, Like) == 1
    assert events(db, "liked") == 1

    assert aru.delete(f"{API}/posts/{post_id}/like").json() == {"liked": False, "like_count": 0}
    aru.delete(f"{API}/posts/{post_id}/like")
    assert count(db, Like) == 0
    assert events(db, "unliked") == 1


def test_fr03_feed_shows_own_and_followed_posts_newest_first(make_client: Clients) -> None:
    aru, dias, timur = make_client(), make_client(), make_client()
    register(aru, "aru")
    dias_id = register(dias, "dias")["id"]
    register(timur, "timur")

    post(dias, "dias 1")
    post(timur, "timur 1")  # not followed: must not appear
    post(aru, "aru 1")
    post(dias, "dias 2")
    aru.post(f"{API}/users/{dias_id}/follow", headers=idem())

    feed = aru.get(f"{API}/feed").json()
    assert [p["body"] for p in feed["items"]] == ["dias 2", "aru 1", "dias 1"]
    assert [p["is_own"] for p in feed["items"]] == [False, True, False]
    assert feed["next_cursor"] is None

    aru.delete(f"{API}/users/{dias_id}/follow")
    assert [p["body"] for p in aru.get(f"{API}/feed").json()["items"]] == ["aru 1"]


def test_fr03_feed_is_cursor_paginated(client: TestClient) -> None:
    register(client, "aru")
    for i in range(5):
        post(client, f"post {i}")

    page1 = client.get(f"{API}/feed", params={"limit": 2}).json()
    page2 = client.get(f"{API}/feed", params={"limit": 2, "cursor": page1["next_cursor"]}).json()
    page3 = client.get(f"{API}/feed", params={"limit": 2, "cursor": page2["next_cursor"]}).json()
    bodies = [p["body"] for page in (page1, page2, page3) for p in page["items"]]
    assert bodies == ["post 4", "post 3", "post 2", "post 1", "post 0"]
    assert page3["next_cursor"] is None
    assert client.get(f"{API}/feed", params={"limit": 51}).status_code == 422
    assert client.get(f"{API}/feed", params={"cursor": "garbage"}).status_code == 400


def test_fr03_comments_are_listed_and_counted(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    post_id = post(dias, "Hello")["id"]

    res = aru.post(f"{API}/posts/{post_id}/comments", json={"body": " Nice! "}, headers=idem())
    assert res.status_code == 201
    assert res.json()["body"] == "Nice!"
    dias.post(f"{API}/posts/{post_id}/comments", json={"body": "Thanks"}, headers=idem())

    thread = aru.get(f"{API}/posts/{post_id}/comments").json()["items"]
    assert [c["body"] for c in thread] == ["Thanks", "Nice!"]
    assert [c["is_own"] for c in thread] == [False, True]
    assert dias.get(f"{API}/feed").json()["items"][0]["comment_count"] == 2
    assert events(db, "commented") == 2


def test_fr03_delete_only_own_post(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    post_id = post(dias, "Mine")["id"]

    assert aru.delete(f"{API}/posts/{post_id}").status_code == 404  # not 403
    assert db.get(Post, post_id).deleted_at is None

    assert dias.delete(f"{API}/posts/{post_id}").status_code == 204
    assert db.get(Post, post_id).deleted_at is not None  # soft delete
    assert dias.get(f"{API}/feed").json()["items"] == []
    assert dias.delete(f"{API}/posts/{post_id}").status_code == 404
    assert aru.post(f"{API}/posts/{post_id}/like", headers=idem()).status_code == 404
    assert aru.get(f"{API}/posts/{post_id}/comments").status_code == 404
    assert events(db, "post_deleted") == 1


def test_fr03_delete_only_own_comment(make_client: Clients, db: Session) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    post_id = post(dias, "Hello")["id"]
    comment_id = aru.post(
        f"{API}/posts/{post_id}/comments", json={"body": "Nice"}, headers=idem()
    ).json()["id"]

    # Even the post's author cannot delete someone else's comment in M0.
    assert dias.delete(f"{API}/comments/{comment_id}").status_code == 404
    assert aru.delete(f"{API}/comments/{comment_id}").status_code == 204
    assert db.get(Comment, comment_id).deleted_at is not None
    assert aru.get(f"{API}/posts/{post_id}/comments").json()["items"] == []
    assert dias.get(f"{API}/feed").json()["items"][0]["comment_count"] == 0
    assert events(db, "comment_deleted") == 1


def test_fr03_post_body_limits(client: TestClient) -> None:
    register(client, "aru")
    assert client.post(f"{API}/posts", json={"body": "   "}, headers=idem()).status_code == 422
    assert client.post(f"{API}/posts", json={"body": "x" * 1001}, headers=idem()).status_code == 422
    assert client.post(f"{API}/posts", json={"body": "x" * 1000}, headers=idem()).status_code == 201


def test_fr03_profile_lists_that_users_posts(make_client: Clients) -> None:
    aru, dias = make_client(), make_client()
    register(aru, "aru")
    register(dias, "dias")
    post(dias, "dias post")
    post(aru, "aru post")
    items = aru.get(f"{API}/users/dias/posts").json()["items"]
    assert [p["body"] for p in items] == ["dias post"]


def test_nfr03_social_endpoints_require_sign_in(client: TestClient) -> None:
    some_id = "00000000-0000-4000-8000-000000000000"
    assert client.get(f"{API}/feed").status_code == 401
    assert client.post(f"{API}/posts", json={"body": "x"}, headers=idem()).status_code == 401
    assert client.delete(f"{API}/posts/{some_id}").status_code == 401
    assert client.post(f"{API}/users/{some_id}/follow", headers=idem()).status_code == 401
    assert client.post(f"{API}/posts/{some_id}/like", headers=idem()).status_code == 401
    assert client.delete(f"{API}/comments/{some_id}").status_code == 401
