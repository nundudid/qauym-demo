import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { Community } from '../api/analytics';
import { card, formatTime } from './ui';

/** The label every analytics view must carry: results are inferred, and dated (DR-04). */
export function InferredLabel({ cutoff }: { cutoff: string | null }) {
  return (
    <p className="mt-1 text-sm text-slate-700">
      <span className="rounded border border-slate-500 px-1.5 py-0.5 font-medium">Inferred</span>{' '}
      {cutoff ? `Inferred by Qauym on ${formatTime(cutoff)}.` : 'Inferred by Qauym.'} You did not
      join this community; it is an estimate from who you follow and interact with.
    </p>
  );
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

export function communityTitle(community: Community): string {
  const interests = community.shared_interests.join(', ');
  return interests ? `${community.name}: ${interests}` : community.name;
}

export default function CommunityCard({
  community,
  heading,
  children,
}: {
  community: Community;
  heading: ReactNode;
  children?: ReactNode;
}) {
  const known = community.known_members;
  return (
    <section className={card} aria-label={`Inferred community: ${community.name}`}>
      {heading}
      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-slate-600">Size</dt>
          <dd>{plural(community.size, 'member')}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Shared interests</dt>
          <dd>
            {community.shared_interests.length > 0
              ? community.shared_interests.join(', ')
              : 'No interest is shared by enough members to show.'}
          </dd>
        </div>
      </dl>

      <h3 className="mt-4 text-sm font-medium text-slate-600">People you know in it</h3>
      {known.length > 0 ? (
        <ul className="mt-1 flex flex-wrap gap-2">
          {known.map((user) => (
            <li key={user.id}>
              <Link
                to={`/u/${user.username}`}
                className="inline-block rounded-md border border-slate-300 px-2 py-1 text-sm underline"
              >
                {user.display_name} <span className="text-slate-600">@{user.username}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-sm">Nobody you follow, or who follows you, yet.</p>
      )}
      <p className="mt-2 text-sm text-slate-700">
        {community.other_member_count > 0
          ? `Plus ${plural(community.other_member_count, 'other member')}. ` +
            'They are counted but not named, because you are not connected to them.'
          : 'There are no other members.'}
      </p>
      {children}
    </section>
  );
}
