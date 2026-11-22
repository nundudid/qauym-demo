import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage, newKey } from '../api/client';
import type { Post } from '../api/types';
import CommentThread from './CommentThread';
import { btnDanger, btnSecondary, card, formatTime, Notice } from './ui';

export default function PostCard({ post }: { post: Post }) {
  const queryClient = useQueryClient();
  const [showComments, setShowComments] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['posts'] });

  const like = useMutation({
    mutationFn: (vars: { like: boolean; key: string }) =>
      vars.like
        ? api(`/posts/${post.id}/like`, { method: 'POST', idempotencyKey: vars.key })
        : api(`/posts/${post.id}/like`, { method: 'DELETE' }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => api<void>(`/posts/${post.id}`, { method: 'DELETE' }),
    onSuccess: refresh,
  });

  const likes = `${post.like_count} ${post.like_count === 1 ? 'like' : 'likes'}`;
  const comments = `${post.comment_count} ${post.comment_count === 1 ? 'comment' : 'comments'}`;

  return (
    <article className={card} aria-label={`Post by ${post.author.display_name}`}>
      <header className="text-sm">
        <Link to={`/u/${post.author.username}`} className="font-semibold underline">
          {post.author.display_name}
        </Link>{' '}
        <span className="text-slate-600">
          @{post.author.username} ·{' '}
          <time dateTime={post.created_at}>{formatTime(post.created_at)}</time>
        </span>
      </header>
      <p className="mt-2 break-words whitespace-pre-wrap">{post.body}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={btnSecondary}
          aria-pressed={post.liked_by_me}
          onClick={() => like.mutate({ like: !post.liked_by_me, key: newKey() })}
          disabled={like.isPending}
        >
          {post.liked_by_me ? '♥ Liked' : '♡ Like'}
          <span className="ml-2 text-slate-600">{likes}</span>
        </button>
        <button
          type="button"
          className={btnSecondary}
          aria-expanded={showComments}
          onClick={() => setShowComments((open) => !open)}
        >
          {showComments ? 'Hide comments' : 'Comments'}
          <span className="ml-2 text-slate-600">{comments}</span>
        </button>
        {post.is_own &&
          (confirmingDelete ? (
            <>
              <button
                type="button"
                className={btnDanger}
                onClick={() => remove.mutate()}
                disabled={remove.isPending}
              >
                Confirm delete
              </button>
              <button
                type="button"
                className={btnSecondary}
                onClick={() => setConfirmingDelete(false)}
              >
                Cancel
              </button>
            </>
          ) : (
            <button type="button" className={btnDanger} onClick={() => setConfirmingDelete(true)}>
              Delete post
            </button>
          ))}
      </div>
      <Notice kind="error">
        {(like.isError && errorMessage(like.error)) ||
          (remove.isError && errorMessage(remove.error))}
      </Notice>
      {showComments && <CommentThread postId={post.id} />}
    </article>
  );
}
