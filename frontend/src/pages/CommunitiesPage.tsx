import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import type { CommunitiesMe } from '../api/analytics';
import { api, errorMessage } from '../api/client';
import CommunityCard, { communityTitle, InferredLabel } from '../components/CommunityCard';
import { card, formatTime, Notice } from '../components/ui';

export default function CommunitiesPage() {
  const mine = useQuery({
    queryKey: ['communities', 'me'],
    queryFn: () => api<CommunitiesMe>('/communities/me'),
  });
  const data = mine.data;

  return (
    <>
      <h1 className="text-2xl font-semibold">My communities</h1>
      <p aria-live="polite" className="text-sm text-slate-600">
        {mine.isPending && 'Loading your inferred community…'}
      </p>
      <Notice kind="error">{mine.isError && errorMessage(mine.error)}</Notice>

      {data?.state === 'member' && data.community && (
        <>
          <InferredLabel cutoff={data.snapshot_cutoff_at} />
          <div className="mt-4">
            <CommunityCard
              community={data.community}
              heading={
                <h2 className="text-lg font-semibold">
                  <Link to={`/communities/${data.community.id}`} className="underline">
                    {communityTitle(data.community)}
                  </Link>
                </h2>
              }
            />
          </div>
        </>
      )}

      {data && data.state !== 'member' && (
        <section className={`${card} mt-4`} aria-label="No inferred community yet">
          <h2 className="text-lg font-semibold">
            {data.state === 'no_run' ? 'Nothing to show yet' : 'You are not in a community yet'}
          </h2>
          <p className="mt-2">{data.message}</p>
          {data.snapshot_cutoff_at && (
            <p className="mt-2 text-sm text-slate-700">
              Communities were last inferred by Qauym on {formatTime(data.snapshot_cutoff_at)}.
            </p>
          )}
          <p className="mt-3">
            <Link to="/people" className="underline">
              Find people to follow
            </Link>
          </p>
        </section>
      )}
    </>
  );
}
