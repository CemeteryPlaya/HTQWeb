import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export type HRLevel = 'senior' | 'junior' | null;

interface HRLevelResponse {
  level: HRLevel;
}

/**
 * Fetches the HR access level of the current user from the backend.
 *   - `'senior'` — full access (Senior HR, superuser, staff)
 *   - `'junior'` — limited access (Junior HR)
 *   - `null`     — no HR access
 */
export function useHRLevel() {
  const { data, isLoading } = useQuery<HRLevelResponse>({
    queryKey: ['hr-level'],
    queryFn: async () => {
      const res = await api.get<HRLevelResponse>('hr/v1/employees/hr-level/');
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // cache for 5 min
    retry: false,
  });

  return {
    level: data?.level ?? null,
    isSenior: data?.level === 'senior',
    isJunior: data?.level === 'junior',
    isLoading,
  };
}
