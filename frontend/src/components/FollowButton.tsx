import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, errorMessage, newKey } from '../api/client';
import { btnPrimary, btnSecondary, Notice } from './ui';

type Props = { userId: string; displayName: string; isFollowing: boolean };

export default function FollowButton({ userId, displayName, isFollowing }: Props) {
  const queryClient = useQueryClient();
  const toggle = useMutation({
    mutationFn: (vars: { follow: boolean; key: string }) =>
      vars.follow
        ? api(`/users/${userId}/follow`, { method: 'POST', idempotencyKey: vars.key })
        : api(`/users/${userId}/follow`, { method: 'DELETE' }),
    onSuccess: () =>
      Promise.all(
        ['people', 'profile', 'posts'].map((key) =>
          queryClient.invalidateQueries({ queryKey: [key] }),
        ),
      ),
  });

  return (
    <div>
      <button
        type="button"
        className={isFollowing ? btnSecondary : btnPrimary}
        aria-label={`${isFollowing ? 'Unfollow' : 'Follow'} ${displayName}`}
        onClick={() => toggle.mutate({ follow: !isFollowing, key: newKey() })}
        disabled={toggle.isPending}
      >
        {isFollowing ? '✓ Following · Unfollow' : 'Follow'}
      </button>
      <Notice kind="error">{toggle.isError && errorMessage(toggle.error)}</Notice>
    </div>
  );
}
