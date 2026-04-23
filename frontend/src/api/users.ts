import api from './client';

export const usersApi = {
  getToken: (email: string, password: string) =>
    api.post('users/v1/token/', { email, password }),
  getProfile: () => api.get('users/v1/profile/me'),
  register: (data: any) => api.post('users/v1/register/', data),
};
