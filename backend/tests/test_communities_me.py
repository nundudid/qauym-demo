"""FR-08, DR-03, DR-04: My communities, its empty states, and who may be named."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from analytics.jobs import run_analytics
from app.models import Membership, User
from tests.factories import follow, like, make_post, make_user
from tests.utils import idem, register

API = "/api/v1"
Clients = Callable[[], TestClient]
# The cutoff lies just ahead of the fixtures, which are created while each test runs.
NOW = datetime.now(UTC) + timedelta(hours=1)


def user_row(db: Session, username: str) -> User:
    return db.scalars(select(User).where(User.username == username)).one()


def world(db: Session, viewer: User) -> dict[str, User]:
    """The viewer's group: a friend they follow, a fan who follows them, and a stranger
    linked to the group only through other people. A second group lives elsewhere."""
    friend = make_user(db, "friend", interests=("hiking", "chess"))
    fan = make_user(db, "fan", interests=("hiking", "chess"))
    stranger = make_user(db, "stranger", interests=("hiking",))
    follow(db, viewer, friend)
    follow(db, fan, viewer)
    for a, b in ((friend, fan), (fan, friend), (stranger, friend), (stranger, fan)):
        follow(db, a, b)
    like(db, viewer, make_post(db, stranger))  # an interaction, but no follow either way

    others = [make_user(db, f"other{i}", interests=("cooking",)) for i in range(4)]
    for a in others:
        for b in others:
            if a is not b:
                follow(db, a, b)
    db.commit()
    return {"friend": friend, "fan": fan, "stranger": stranger, "other": others[0]}


def test_fr08_no_run_yet(client: TestClient) -> None:
    register(client, "aru")
    body = client.get(f"{API}/communities/me").json()
    assert body["state"] == "no_run"
    assert body["inferred"] is True
    assert body["community"] is None and body["run_id"] is None
    assert body["message"]


def test_fr08_ordinary_member_sees_their_inferred_community(
    client: TestClient, db: Session
) -> None:
    register(client, "aru")
    client.patch(f"{API}/me", json={"interests": ["hiking"]})
    people = world(db, user_row(db, "aru"))
    run = next(r for r in run_analytics(db, cutoff=NOW).runs if r.algorithm == "leiden")

    body = client.get(f"{API}/communities/me").json()
    assert body["state"] == "member"
    assert body["inferred"] is True
    assert body["run_id"] == str(run.id)
    assert datetime.fromisoformat(body["snapshot_cutoff_at"]) == NOW

    community = body["community"]
    assert community["name"].startswith("Community ")
    assert community["size"] == 4
    assert community["shared_interests"] == ["hiking"]  # chess has only 2 members
    # Named: the person I follow and the person who follows me. Counted: everyone else.
    assert [m["username"] for m in community["known_members"]] == ["fan", "friend"]
    assert community["other_member_count"] == 1
    assert people["stranger"].username not in str(body)
    assert "email" not in str(community)
    assert 0 < community["strength"] <= 1


def test_fr08_isolated_user_gets_the_empty_state(make_client: Clients, db: Session) -> None:
    aru, lonely = make_client(), make_client()
    register(aru, "aru")
    register(lonely, "lonely")
    world(db, user_row(db, "aru"))
    run_analytics(db, cutoff=NOW)

    body = lonely.get(f"{API}/communities/me").json()
    assert body["state"] == "not_in_graph"
    assert body["community"] is None
    assert body["run_id"] is not None and body["snapshot_cutoff_at"] is not None
    assert "not in an inferred community yet" in body["message"]


def test_fr08_stale_snapshot_shows_its_timestamp(make_client: Clients, db: Session) -> None:
    aru, late = make_client(), make_client()
    register(aru, "aru")
    people = world(db, user_row(db, "aru"))
    old_cutoff = datetime.now(UTC)
    run_analytics(db, cutoff=old_cutoff)

    # Activity after the snapshot does not change the result until the next run.
    late_id = register(late, "late")["id"]
    aru.post(f"{API}/users/{late_id}/follow", headers=idem())
    late.post(f"{API}/users/{people['friend'].id}/follow", headers=idem())

    mine = aru.get(f"{API}/communities/me").json()
    assert datetime.fromisoformat(mine["snapshot_cutoff_at"]) == old_cutoff
    assert mine["community"]["size"] == 4
    assert late.get(f"{API}/communities/me").json()["state"] == "not_in_graph"


def test_fr08_community_detail_names_only_known_members(client: TestClient, db: Session) -> None:
    register(client, "aru")
    people = world(db, user_row(db, "aru"))
    run = next(r for r in run_analytics(db, cutoff=NOW).runs if r.algorithm == "leiden")
    mine = client.get(f"{API}/communities/me").json()["community"]

    detail = client.get(f"{API}/communities/{mine['id']}").json()
    assert detail["inferred"] is True and detail["run_id"] == str(run.id)
    assert detail["community"] == mine

    # Another community, and an unknown id, look the same: 404 (D-014).
    other = db.get(Membership, (run.id, people["other"].id)).community_id
    assert client.get(f"{API}/communities/{other}").status_code == 404
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.get(f"{API}/communities/{missing}").status_code == 404


def test_fr08_deleted_members_are_neither_named_nor_counted(
    client: TestClient, db: Session
) -> None:
    register(client, "aru")
    people = world(db, user_row(db, "aru"))
    run_analytics(db, cutoff=NOW)
    db.execute(
        update(User).where(User.id == people["friend"].id).values(deleted_at=datetime.now(UTC))
    )
    db.commit()

    community = client.get(f"{API}/communities/me").json()["community"]
    assert [m["username"] for m in community["known_members"]] == ["fan"]
    assert community["size"] == 3


def test_nfr03_communities_and_admin_require_the_right_user(
    make_client: Clients, db: Session
) -> None:
    anonymous, aru, boss = make_client(), make_client(), make_client()
    assert anonymous.get(f"{API}/communities/me").status_code == 401
    assert anonymous.get(f"{API}/admin/analytics/runs").status_code == 401
    assert anonymous.post(f"{API}/admin/analytics/runs").status_code == 401

    register(aru, "aru")
    assert aru.get(f"{API}/admin/analytics/runs").status_code == 404
    assert aru.post(f"{API}/admin/analytics/runs").status_code == 404

    register(boss, "boss")
    db.execute(update(User).where(User.username == "boss").values(role="admin"))
    db.commit()
    world(db, user_row(db, "aru"))

    started = boss.post(f"{API}/admin/analytics/runs")
    assert started.status_code == 201 and started.json()["started"] is True
    again = boss.post(f"{API}/admin/analytics/runs")  # a double click in the same minute
    assert again.status_code == 200 and again.json()["started"] is False

    runs = boss.get(f"{API}/admin/analytics/runs").json()["items"]
    assert sorted(r["algorithm"] for r in runs) == ["leiden", "louvain"]
    leiden = next(r for r in runs if r["algorithm"] == "leiden")
    assert leiden["status"] == "published" and leiden["is_active"] is True
    assert leiden["n_communities"] == 2 and leiden["node_count"] == 8
    assert aru.get(f"{API}/communities/me").json()["state"] == "member"
