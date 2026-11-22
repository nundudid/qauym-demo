import uuid

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, Db
from app.models import Community, Membership, User
from app.schemas.analytics import CommunitiesMeOut, CommunityDetailOut, CommunityOut
from app.services import visibility
from app.services.posts import brief

router = APIRouter(tags=["communities"])


def community_out(
    db: Session, viewer: User, community: Community, membership: Membership | None
) -> CommunityOut:
    known = visibility.known_community_members(db, viewer, community)
    size = visibility.community_member_count(db, viewer, community)
    interests = [item["tag"] for item in community.summary.get("top_interests", [])]
    return CommunityOut(
        id=community.id,
        name=f"Community {community.label + 1}",
        shared_interests=interests[:3],
        size=size,
        known_members=[brief(u) for u in known],
        other_member_count=max(0, size - len(known) - 1),  # minus the viewer
        strength=membership.strength if membership else None,
    )


@router.get("/communities/me", response_model=CommunitiesMeOut)
def my_community(user: CurrentUser, db: Db) -> CommunitiesMeOut:
    """The viewer's inferred community from the active run, or an explicit empty state."""
    active = visibility.active_run(db)
    if active is None:
        return CommunitiesMeOut(
            state="no_run",
            message="Qauym has not inferred any communities yet. Check back soon.",
            run_id=None,
            snapshot_cutoff_at=None,
            community=None,
        )
    run, snapshot = active
    membership = visibility.viewer_membership(db, user, run)
    community = db.get(Community, membership.community_id) if membership else None
    if membership is None or community is None:
        return CommunitiesMeOut(
            state="not_in_graph",
            message=(
                "You are not in an inferred community yet. Follow people and like or "
                "comment on their posts, and you will appear after the next update."
            ),
            run_id=run.id,
            snapshot_cutoff_at=snapshot.cutoff_at,
            community=None,
        )
    return CommunitiesMeOut(
        state="member",
        message="Inferred from who you follow and interact with.",
        run_id=run.id,
        snapshot_cutoff_at=snapshot.cutoff_at,
        community=community_out(db, user, community, membership),
    )


@router.get("/communities/{community_id}", response_model=CommunityDetailOut)
def read_community(community_id: uuid.UUID, user: CurrentUser, db: Db) -> CommunityDetailOut:
    community = visibility.get_viewer_community(db, user, community_id)
    active = visibility.active_run(db)
    assert active is not None  # get_viewer_community raised otherwise
    run, snapshot = active
    membership = visibility.viewer_membership(db, user, run)
    return CommunityDetailOut(
        run_id=run.id,
        snapshot_cutoff_at=snapshot.cutoff_at,
        community=community_out(db, user, community, membership),
    )
