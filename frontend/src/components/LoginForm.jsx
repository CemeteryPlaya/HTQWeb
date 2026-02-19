import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../api/client';

function LoginForm({ onLogin }) {
    const { t } = useTranslation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const login = async (e) => {
        e.preventDefault();
        try {
            const res = await api.post('token/', { email, password });
            localStorage.setItem('access', res.data.access);
            localStorage.setItem('refresh', res.data.refresh);

            // Ensure axios instance has Authorization header set
            try {
                const client = await api.getClient();
                client.defaults.headers.common['Authorization'] = `Bearer ${res.data.access}`;
            } catch (clientErr) {
                console.warn('Could not set default Authorization header on api client', clientErr);
            }

            if (onLogin) onLogin();
        } catch (err) {
            console.error(err);
            // Try to show server-provided message if available
            const serverMsg = err?.response?.data || err?.message || 'Login failed';
            if (typeof serverMsg === 'string') setError(serverMsg);
            else if (serverMsg.detail) setError(serverMsg.detail);
            else setError('Login failed');
        }
    };

    return (
        <form onSubmit={login} className="p-4 border rounded shadow-md max-w-sm mx-auto mt-4">
            <h2 className="text-xl mb-4">{t('auth.login')}</h2>
            {error && <p className="text-red-500 mb-2">{error}</p>}
            <div className="mb-4">
                <label className="block mb-1">{t('auth.email')}</label>
                <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full p-2 border rounded"
                    placeholder="email@example.com"
                />
            </div>
            <div className="mb-4">
                <label className="block mb-1">{t('auth.password')}</label>
                <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full p-2 border rounded"
                />
            </div>
            <button type="submit" className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">
                {t('auth.login')}
            </button>
        </form>
    );
}

export default LoginForm;
