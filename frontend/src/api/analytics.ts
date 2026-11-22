import type { UserBrief } from './types';

export type Community = {
  id: string;
  name: string;
  shared_interests: string[];
  size: number;
  known_members: UserBrief[];
  other_member_count: number;
  strength: number | null;
};

export type CommunitiesMe = {
  state: 'member' | 'not_in_graph' | 'no_run';
  message: string;
  inferred: true;
  run_id: string | null;
  snapshot_cutoff_at: string | null;
  community: Community | null;
};

export type CommunityDetail = {
  inferred: true;
  run_id: string;
  snapshot_cutoff_at: string;
  community: Community;
};

export type Run = {
  id: string;
  algorithm: string;
  status: string;
  trigger: string;
  started_at: string;
  duration_ms: number | null;
  modularity: number | null;
  n_communities: number | null;
  error_message: string | null;
  snapshot_cutoff_at: string | null;
  node_count: number | null;
  edge_count: number | null;
  is_active: boolean;
};

export type RunTrigger = { started: boolean; reason: string; runs: Run[] };
