import axios from 'axios';

// Try to detect working API base URL automatically.
// Strategy:
// 1. If VITE_API_BASE_URL provided, try it first.
// 2. Try same host with default backend port 8000.
// 3. Try localhost/127.0.0.1:8000.
// For each candidate we perform a lightweight GET to 'v1/register/' —
// a reachable response (even 4xx/5xx) means the backend is reachable and usable.

const ENV_API = import.meta.env.VITE_API_BASE_URL || '';

function buildCandidates() {
    const candidates = [];
    if (ENV_API) candidates.push(ENV_API);

    if (typeof window !== 'undefined') {
        const proto = window.location.protocol || 'http:';
        const host = window.location.hostname;

        // If frontend served on same host, try replacing port with 8000
        candidates.push(`${proto}//${host}:8000/api/`);
        // Also try same origin + /api/ (useful when backend proxied to same origin)
        candidates.push(`${proto}//${host}${window.location.port ? ':' + window.location.port : ''}/api/`);
    }

    // Common local fallbacks
    candidates.push('http://localhost:8000/api/');
    candidates.push('http://127.0.0.1:8000/api/');
    candidates.push('https://localhost:8000/api/');
    return Array.from(new Set(candidates));
}

async function probeCandidate(base) {
    try {
        // Ensure base ends with /api/
        const baseUrl = base.endsWith('/api/') ? base : (base.endsWith('/') ? base + 'api/' : base + '/api/');
        const url = baseUrl + 'v1/register/';
        // Use axios without baseURL so we can probe arbitrary URL
        const res = await axios.get(url, { timeout: 2000 });
        // Got a response (2xx) — candidate works
        return baseUrl;
    } catch (err) {
        // If server responded (4xx/5xx) it's still reachable and acceptable
        if (err && err.response) {
            return base;
        }
        // Network error / no response — candidate not reachable
        return null;
    }
}

let _clientPromise = null;

function createApiClientInstance(base) {
    const client = axios.create({ baseURL: base, withCredentials: false });

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
            if (error.response?.status === 401 && !error.config._retry && !isAuthEndpoint) {
                error.config._retry = true;
                try {
                    const refresh = localStorage.getItem('refresh');
                    if (!refresh) throw new Error('No refresh token');
                    const res = await axios.post(base + 'token/refresh/', { refresh });
                    localStorage.setItem('access', res.data.access);
                    client.defaults.headers.common['Authorization'] = 'Bearer ' + res.data.access;
                    return client(error.config);
                } catch (refreshError) {
                    console.error('Refresh token failed', refreshError);
                    localStorage.removeItem('access');
                    localStorage.removeItem('refresh');
                    return Promise.reject(refreshError);
                }
            }
            return Promise.reject(error);
        }
    );

    return client;
}

async function detectApiBase() {
    const candidates = buildCandidates();
    // Debug: print candidates tried
    try {
        console.debug('[api-detector] candidates:', candidates);
    } catch (e) {
        // ignore in non-browser environments
    }
    for (const c of candidates) {
        const ok = await probeCandidate(c);
        if (ok) return ok;
    }
    // last resort
    const fallback = ENV_API || 'http://localhost:8000/api/';
    try {
        console.warn('[api-detector] falling back to', fallback);
    } catch (e) { }
    return fallback;
}

function ensureClient() {
    if (!_clientPromise) {
        _clientPromise = (async () => {
            const base = await detectApiBase();
            return createApiClientInstance(base);
        })();
    }
    return _clientPromise;
}

// Export a proxy with common axios methods that wait for detection to finish.
const methods = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'];

const api = {};
for (const m of methods) {
    api[m] = async function (...args) {
        const client = await ensureClient();
        return client[m](...args);
    };
}

// Also expose a way to get raw axios instance (async)
api.getClient = ensureClient;

export default api;
