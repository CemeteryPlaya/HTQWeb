import type { UserProfile } from '@/types/userProfile';

export const ACCESS_TOKEN_KEY = 'access';
export const REFRESH_TOKEN_KEY = 'refresh';
export const CACHED_PROFILE_KEY = 'cached_profile';

export const profileQueryKey = ['profile'] as const;

export const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

export const readCachedProfile = (): UserProfile | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  const cached = localStorage.getItem(CACHED_PROFILE_KEY);
  if (!cached) {
    return null;
  }

  try {
    return JSON.parse(cached) as UserProfile;
  } catch {
    localStorage.removeItem(CACHED_PROFILE_KEY);
    return null;
  }
};

export const writeCachedProfile = (profile: UserProfile): void => {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.setItem(CACHED_PROFILE_KEY, JSON.stringify(profile));
};

export const clearAuthStorage = (): void => {
  if (typeof window === 'undefined') {
    return;
  }

  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(CACHED_PROFILE_KEY);
};
