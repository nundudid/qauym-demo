import { useQuery } from '@tanstack/react-query';
import { api, ApiError } from '../api/client';
import type { Me } from '../api/types';

export const ME_KEY = ['me'] as const;

/** The signed-in user, or null when there is no valid session. */
export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: async (): Promise<Me | null> => {
      try {
        return await api<Me>('/me');
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}
