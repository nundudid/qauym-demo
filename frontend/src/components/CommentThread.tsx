import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, errorMessage, newKey } from '../api/client';
import type { Comment, Page } from '../api/types';
import { COMMENT_MAX } from '../validation';
import { btnDanger, btnPrimary, formatTime, inputClass, Notice } from './ui';

export default function CommentThread({ postId }: { postId: string }) {
  const id = useId();
  const queryClient = useQueryClient();
  const [body, setBody] = useState('');
  const comments = useQuery({
    queryKey: ['comments', postId],
    queryFn: () => api<Page<Comment>>(`/posts/${postId}/comments?limit=50`),
  });
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['comments', postId] }),
      queryClient.invalidateQueries({ queryKey: ['posts'] }),
    ]);
  const add = useMutation({
    mutationFn: (vars: { body: string; key: string }) =>
      api<Comment>(`/posts/${postId}/comments`, {
        method: 'POST',
        body: { body: vars.body },
        idempotencyKey: vars.key,
      }),
    onSuccess: () => {
      setBody('');
      return refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (commentId: string) => api<void>(`/comments/${commentId}`, { method: 'DELETE' }),
    onSuccess: refresh,
  });

  const tooLong = body.length > COMMENT_MAX;
  const canSend = body.trim().length > 0 && !tooLong && !add.isPending;
  // The API returns newest first; a thread reads better oldest first.
  const items = [...(comments.data?.items ?? [])].reverse();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (canSend) add.mutate({ body, key: newKey() });
  }

  return (
    <section aria-label="Comments" className="mt-3 border-t border-slate-200 pt-3">
      {comments.isPending && <p className="text-sm">Loading comments…</p>}
      <Notice kind="error">{comments.isError && errorMessage(comments.error)}</Notice>
      {comments.data?.next_cursor && (
        <p className="text-sm text-slate-600">Showing the latest 50 comments.</p>
      )}
      {comments.data && items.length === 0 && (
        <p className="text-sm text-slate-600">No comments yet.</p>
      )}
      <ul className="space-y-2">
        {items.map((comment) => (
          <li key={comment.id} className="rounded-md bg-slate-100 p-2 text-sm">
            <p>
              <Link to={`/u/${comment.author.username}`} className="font-medium underline">
                {comment.author.display_name}
              </Link>{' '}
              <span className="text-slate-600">· {formatTime(comment.created_at)}</span>
            </p>
            <p className="mt-1 break-words whitespace-pre-wrap">{comment.body}</p>
            {comment.is_own && (
              <button
                type="button"
                className={`${btnDanger} mt-1 px-2 py-1`}
                onClick={() => remove.mutate(comment.id)}
                disabled={remove.isPending}
              >
                Delete comment
              </button>
            )}
          </li>
        ))}
      </ul>
      <Notice kind="error">{remove.isError && errorMessage(remove.error)}</Notice>

      <form onSubmit={submit} className="mt-3">
        <label htmlFor={id} className="block text-sm font-medium">
          Add a comment
        </label>
        <textarea
          id={id}
          rows={2}
          className={inputClass}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          aria-describedby={`${id}-count`}
          aria-invalid={tooLong || undefined}
        />
        <div className="mt-2 flex items-center justify-between gap-3">
          <p
            id={`${id}-count`}
            className={`text-sm ${tooLong ? 'text-red-800' : 'text-slate-600'}`}
          >
            {body.length} / {COMMENT_MAX} characters{tooLong && ' — too long'}
          </p>
          <button type="submit" className={btnPrimary} disabled={!canSend}>
            {add.isPending ? 'Sending…' : 'Comment'}
          </button>
        </div>
        <Notice kind="error">{add.isError && errorMessage(add.error)}</Notice>
      </form>
    </section>
  );
}
