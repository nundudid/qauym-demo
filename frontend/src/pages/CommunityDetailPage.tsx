import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import type { CommunityDetail } from '../api/analytics';
import { api, ApiError, errorMessage } from '../api/client';
import CommunityCard, { communityTitle, InferredLabel } from '../components/CommunityCard';
import { Notice } from '../components/ui';

export default function CommunityDetailPage() {
  const { id = '' } = useParams();
  const detail = useQuery({
    queryKey: ['communities', id],
    queryFn: () => api<CommunityDetail>(`/communities/${encodeURIComponent(id)}`),
    retry: false,
  });
  const missing = detail.error instanceof ApiError && detail.error.status === 404;

  return (
    <>
      <p className="text-sm">
        <Link to="/communities" className="underline">
          ← My communities
        </Link>
      </p>
      <p aria-live="polite" className="text-sm text-slate-600">
        {detail.isPending && 'Loading the community…'}
      </p>
      {missing ? (
        <>
          <h1 className="mt-2 text-2xl font-semibold">Community not found</h1>
          <p className="mt-2">
            This inferred community does not exist any more, or you are not part of it. Communities
            change each time Qauym updates them.
          </p>
        </>
      ) : (
        <Notice kind="error">{detail.isError && errorMessage(detail.error)}</Notice>
      )}

      {detail.data && (
        <>
          <h1 className="mt-2 text-2xl font-semibold">{communityTitle(detail.data.community)}</h1>
          <InferredLabel cutoff={detail.data.snapshot_cutoff_at} />
          <div className="mt-4">
            <CommunityCard
              community={detail.data.community}
              heading={<h2 className="text-lg font-semibold">About this inferred community</h2>}
            >
              {detail.data.community.strength !== null && (
                <p className="mt-3 text-sm text-slate-700">
                  About {Math.round(detail.data.community.strength * 100)}% of your follows and
                  interactions are with people in this community.
                </p>
              )}
            </CommunityCard>
          </div>
        </>
      )}
    </>
  );
}
