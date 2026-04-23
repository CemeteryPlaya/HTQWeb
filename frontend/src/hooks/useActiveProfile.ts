import { useQuery } from '@tanstack/react-query';

import api from '@/api/client';
import type { UserProfile } from '@/types/userProfile';
import {
  clearAuthStorage,
  getAccessToken,
  profileQueryKey,
  readCachedProfile,
  writeCachedProfile,
} from '@/lib/auth/profileStorage';

interface UseActiveProfileOptions {
  enabled?: boolean;
  retry?: boolean;
  staleTime?: number;
}

export const useActiveProfile = (options: UseActiveProfileOptions = {}) => {
  const token = getAccessToken();
  const isLoggedIn = Boolean(token);

  const query = useQuery({
    queryKey: profileQueryKey,
    queryFn: async () => {
      const response = await api.get<UserProfile>('users/v1/profile/me');
      writeCachedProfile(response.data);
      return response.data;
    },
    enabled: options.enabled ?? isLoggedIn,
    retry: options.retry ?? false,
    staleTime: options.staleTime,
  });

  const activeProfile = query.data ?? readCachedProfile();

  return {
    ...query,
    activeProfile,
    isLoggedIn,
    token,
    clearAuthStorage,
  };
};
