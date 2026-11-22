import { useInfiniteQuery } from '@tanstack/react-query';
import { api, errorMessage } from '../api/client';
import type { Page, Post } from '../api/types';
import PostCard from './PostCard';
import { btnSecondary, Notice } from './ui';

type Props = {
  /** Must start with 'posts' so mutations refresh every list. */
  queryKey: readonly string[];
  /** API path that returns a page of posts, e.g. '/feed'. */
  path: string;
  emptyText: string;
};

export default function PostList({ queryKey, path, emptyText }: Props) {
  const posts = useInfiniteQuery({
    queryKey,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      api<Page<Post>>(pageParam ? `${path}?cursor=${encodeURIComponent(pageParam)}` : path),
    getNextPageParam: (last) => last.next_cursor,
  });
  const items = posts.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <section aria-label="Posts" className="mt-4 space-y-4">
      {posts.isPending && <p>Loading posts…</p>}
      <Notice kind="error">{posts.isError && errorMessage(posts.error)}</Notice>
      {posts.data && items.length === 0 && <p className="text-slate-700">{emptyText}</p>}
      {items.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
      {posts.hasNextPage && (
        <button
          type="button"
          className={btnSecondary}
          onClick={() => posts.fetchNextPage()}
          disabled={posts.isFetchingNextPage}
        >
          {posts.isFetchingNextPage ? 'Loading…' : 'Load more posts'}
        </button>
      )}
    </section>
  );
}
