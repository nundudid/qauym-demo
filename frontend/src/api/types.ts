export type Me = {
  id: string;
  email: string;
  username: string;
  display_name: string;
  bio: string;
  interests: string[];
  role: 'user' | 'moderator' | 'admin';
  inference_opt_out: boolean;
  created_at: string;
};

export type UserBrief = { id: string; username: string; display_name: string };

export type UserListItem = UserBrief & { bio: string; is_following: boolean; is_self: boolean };

export type Profile = UserBrief & {
  bio: string;
  interests: string[];
  follower_count: number;
  following_count: number;
  is_following: boolean;
  follows_you: boolean;
  is_self: boolean;
  created_at: string;
};

export type Post = {
  id: string;
  author: UserBrief;
  body: string;
  created_at: string;
  like_count: number;
  comment_count: number;
  liked_by_me: boolean;
  is_own: boolean;
};

export type Comment = {
  id: string;
  post_id: string;
  author: UserBrief;
  body: string;
  created_at: string;
  is_own: boolean;
};

export type Page<T> = { items: T[]; next_cursor: string | null };
