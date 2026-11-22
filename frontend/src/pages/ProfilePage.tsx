import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError, errorMessage } from '../api/client';
import type { Profile } from '../api/types';
import FollowButton from '../components/FollowButton';
import PostList from '../components/PostList';
import { btnSecondary, card, Notice } from '../components/ui';

export default function ProfilePage() {
  const { username = '' } = useParams();
  const profile = useQuery({
    queryKey: ['profile', username],
    queryFn: () => api<Profile>(`/users/${encodeURIComponent(username)}`),
  });

  if (profile.isPending) return <p>Loading profile…</p>;
  if (profile.isError) {
    const missing = profile.error instanceof ApiError && profile.error.status === 404;
    return (
      <>
        <h1 className="text-2xl font-semibold">{missing ? 'User not found' : 'Profile'}</h1>
        <Notice kind="error">
          {missing ? `There is no user called @${username}.` : errorMessage(profile.error)}
        </Notice>
      </>
    );
  }

  const user = profile.data;
  return (
    <>
      <section className={card} aria-label="Profile">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold break-words">{user.display_name}</h1>
            <p className="text-slate-600">
              @{user.username}
              {user.follows_you && ' · Follows you'}
            </p>
          </div>
          {user.is_self ? (
            <Link to="/settings/profile" className={btnSecondary}>
              Edit profile
            </Link>
          ) : (
            <FollowButton
              userId={user.id}
              displayName={user.display_name}
              isFollowing={user.is_following}
            />
          )}
        </div>
        {user.bio && <p className="mt-3 break-words whitespace-pre-wrap">{user.bio}</p>}
        {user.interests.length > 0 && (
          <ul aria-label="Interests" className="mt-3 flex flex-wrap gap-2">
            {user.interests.map((tag) => (
              <li key={tag} className="rounded-full border border-slate-400 px-2 py-0.5 text-sm">
                {tag}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-sm">
          <strong>{user.follower_count}</strong>{' '}
          {user.follower_count === 1 ? 'follower' : 'followers'} ·{' '}
          <strong>{user.following_count}</strong> following
        </p>
      </section>

      <h2 className="mt-6 text-xl font-semibold">Posts</h2>
      <PostList
        queryKey={['posts', 'user', user.username]}
        path={`/users/${encodeURIComponent(user.username)}/posts`}
        emptyText="No posts yet."
      />
    </>
  );
}
