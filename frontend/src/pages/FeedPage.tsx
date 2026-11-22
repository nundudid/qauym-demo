import PostComposer from '../components/PostComposer';
import PostList from '../components/PostList';

export default function FeedPage() {
  return (
    <>
      <h1 className="mb-4 text-2xl font-semibold">Feed</h1>
      <PostComposer />
      <p className="mt-4 text-sm text-slate-600">
        Your posts and posts from people you follow, newest first.
      </p>
      <PostList
        queryKey={['posts', 'feed']}
        path="/feed"
        emptyText="Nothing here yet. Write a post, or find people to follow on the People page."
      />
    </>
  );
}
