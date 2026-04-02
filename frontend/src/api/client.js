import axios from 'axios';

// API base URL: always use relative '/api/' path.
// In dev: Vite proxy forwards /api → http://127.0.0.1:8000
// In prod: Nginx proxies /api → backend container
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/';

const client = axios.create({
    baseURL: API_BASE,
    withCredentials: true,
    headers: {
        'ngrok-skip-browser-warning': 'true'
    }
});

// Attach auth header from localStorage
client.interceptors.request.use(config => {
    // Skip auth token for public contact request creation or registration
    const isPublicPost = (config.url.includes('v1/contact-requests/') || config.url.includes('v1/register/')) && config.method === 'post';

    if (!isPublicPost) {
        const token = localStorage.getItem('access');
        if (token) {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

// Token refresh logic
client.interceptors.response.use(
    response => response,
    async error => {
        const url = error.config?.url || '';
        // Don't try to refresh for auth endpoints themselves
        const isAuthEndpoint = url.includes('token/') || url.includes('register/');

        // ---- 401: token expired → refresh ----
        if (error.response?.status === 401 && !error.config._retry && !isAuthEndpoint) {
            error.config._retry = true;
            try {
                const refresh = localStorage.getItem('refresh');
                if (!refresh) throw new Error('No refresh token');
                const res = await axios.post(API_BASE + 'token/refresh/', { refresh });
                localStorage.setItem('access', res.data.access);
                if (res.data.refresh) {
                    localStorage.setItem('refresh', res.data.refresh);
                }
                client.defaults.headers.common['Authorization'] = 'Bearer ' + res.data.access;
                error.config.headers['Authorization'] = 'Bearer ' + res.data.access;
                return client(error.config);
            } catch (refreshError) {
                console.error('Refresh token failed', refreshError);
                localStorage.removeItem('access');
                localStorage.removeItem('refresh');
                localStorage.removeItem('cached_profile');
                // Redirect to login so the user can re-authenticate
                if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
                    window.location.href = '/login';
                }
                return Promise.reject(refreshError);
            }
        }

        // ---- 403: might be stale token with outdated claims → try refresh once ----
        if (error.response?.status === 403 && !error.config._retry403 && !isAuthEndpoint) {
            error.config._retry403 = true;
            try {
                const refresh = localStorage.getItem('refresh');
                if (!refresh) throw new Error('No refresh token');
                const res = await axios.post(API_BASE + 'token/refresh/', { refresh });
                localStorage.setItem('access', res.data.access);
                if (res.data.refresh) {
                    localStorage.setItem('refresh', res.data.refresh);
                }
                client.defaults.headers.common['Authorization'] = 'Bearer ' + res.data.access;
                error.config.headers['Authorization'] = 'Bearer ' + res.data.access;
                return client(error.config);
            } catch (_refreshErr) {
                // Refresh didn't help — it's a real permission denial.
                // Fall through to normal error handling.
                console.warn('[api] 403 after token refresh — real permission denial', url);
            }
        }

        return Promise.reject(error);
    }
);

// Expose getClient for backward compatibility
client.getClient = () => Promise.resolve(client);

export default client;

