import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent } from 'react';
import { api, errorMessage, newKey } from '../api/client';
import type { Post } from '../api/types';
import { POST_MAX } from '../validation';
import { btnPrimary, card, inputClass, Notice } from './ui';

export default function PostComposer() {
  const id = useId();
  const queryClient = useQueryClient();
  const [body, setBody] = useState('');
  const create = useMutation({
    mutationFn: (vars: { body: string; key: string }) =>
      api<Post>('/posts', { method: 'POST', body: { body: vars.body }, idempotencyKey: vars.key }),
    onSuccess: () => {
      setBody('');
      return queryClient.invalidateQueries({ queryKey: ['posts'] });
    },
  });

  const tooLong = body.length > POST_MAX;
  const canPost = body.trim().length > 0 && !tooLong && !create.isPending;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (canPost) create.mutate({ body, key: newKey() });
  }

  return (
    <form onSubmit={submit} className={card} aria-label="New post">
      <label htmlFor={id} className="block text-sm font-medium">
        Write a post
      </label>
      <textarea
        id={id}
        rows={3}
        className={inputClass}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        aria-describedby={`${id}-count`}
        aria-invalid={tooLong || undefined}
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <p id={`${id}-count`} className={`text-sm ${tooLong ? 'text-red-800' : 'text-slate-600'}`}>
          {body.length} / {POST_MAX} characters{tooLong && ' — too long'}
        </p>
        <button type="submit" className={btnPrimary} disabled={!canPost}>
          {create.isPending ? 'Posting…' : 'Post'}
        </button>
      </div>
      <Notice kind="error">{create.isError && errorMessage(create.error)}</Notice>
    </form>
  );
}
