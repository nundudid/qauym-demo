import { useQuery } from '@tanstack/react-query';
import { useEffect, useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import type { UserListItem } from '../api/types';
import FollowButton from '../components/FollowButton';
import { card, inputClass, Notice } from '../components/ui';

export default function PeoplePage() {
  const id = useId();
  const [text, setText] = useState('');
  const [query, setQuery] = useState('');

  // Search shortly after the user stops typing.
  useEffect(() => {
    const timer = setTimeout(() => setQuery(text.trim()), 250);
    return () => clearTimeout(timer);
  }, [text]);

  const people = useQuery({
    queryKey: ['people', query],
    queryFn: () =>
      api<{ items: UserListItem[] }>(`/users?limit=50&query=${encodeURIComponent(query)}`),
    placeholderData: (previous) => previous,
  });
  const items = people.data?.items ?? [];

  return (
    <>
      <h1 className="mb-4 text-2xl font-semibold">People</h1>
      <form role="search" onSubmit={(e) => e.preventDefault()}>
        <label htmlFor={id} className="block text-sm font-medium">
          Search by username or name
        </label>
        <input
          id={id}
          type="search"
          className={inputClass}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </form>

      <p aria-live="polite" className="mt-3 text-sm text-slate-600">
        {people.isPending
          ? 'Loading people…'
          : people.data &&
            (query
              ? `${items.length} ${items.length === 1 ? 'result' : 'results'} for “${query}”.`
              : 'Newest members.')}
      </p>
      <Notice kind="error">{people.isError && errorMessage(people.error)}</Notice>

      <ul className="mt-3 space-y-3">
        {items.map((user) => (
          <li key={user.id} className={`${card} flex flex-wrap items-start justify-between gap-3`}>
            <div className="min-w-0">
              <Link to={`/u/${user.username}`} className="font-semibold break-words underline">
                {user.display_name}
              </Link>
              <p className="text-sm text-slate-600">@{user.username}</p>
              {user.bio && <p className="mt-1 text-sm break-words">{user.bio}</p>}
            </div>
            {user.is_self ? (
              <span className="text-sm text-slate-600">This is you</span>
            ) : (
              <FollowButton
                userId={user.id}
                displayName={user.display_name}
                isFollowing={user.is_following}
              />
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
