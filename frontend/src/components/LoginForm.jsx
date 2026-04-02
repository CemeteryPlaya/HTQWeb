import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../api/client';

function LoginForm({ onLogin }) {
    const { t } = useTranslation();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const requestToken = async (loginId, userPassword) => {
        const payload = {
            email: loginId,
            password: userPassword,
        };

        try {
            return await api.post('token/', payload, {
                headers: {
                    'Content-Type': 'application/json',
                },
            });
        } catch (jsonErr) {
            const status = jsonErr?.response?.status;
            const shouldRetryAsForm = status === 400 || status === 401 || status === 415;
            if (!shouldRetryAsForm) {
                throw jsonErr;
            }

            const formData = new URLSearchParams();
            formData.set('email', loginId);
            formData.set('password', userPassword);

            return api.post('token/', formData.toString(), {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });
        }
    };

    const login = async (e) => {
        e.preventDefault();
        setError('');

        const loginId = email.trim();
        if (!loginId || !password) {
            setError('Введите email/телефон и пароль.');
            return;
        }

        try {
            const res = await requestToken(loginId, password);
            const accessToken =
                res?.data?.access ||
                res?.data?.access_token ||
                res?.data?.token ||
                '';

            if (!accessToken) {
                throw new Error('Token response does not contain access token');
            }

            localStorage.setItem('access', accessToken);

            if (res?.data?.refresh) {
                localStorage.setItem('refresh', res.data.refresh);
            }

            // Ensure axios instance has Authorization header set
            try {
                const client = await api.getClient();
                client.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
            } catch (clientErr) {
                console.warn('Could not set default Authorization header on api client', clientErr);
            }

            if (onLogin) onLogin();
        } catch (err) {
            console.error(err);
            const status = err?.response?.status;
            const hasResponseBody = Boolean(err?.response?.data);

            if (status === 401) {
                setError('Неверный логин или пароль. Проверьте данные.');
                return;
            }

            if (status === 500 && !hasResponseBody) {
                setError('Backend API недоступен. Запусти backend на 127.0.0.1:8000 (или укажи VITE_BACKEND_HTTP_TARGET).');
                return;
            }
            if (!status) {
                setError('Ошибка соединения с сервером авторизации.');
                return;
            }
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
                <label className="block mb-1">{t('auth.emailOrPhone')}</label>
                <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full p-2 border rounded"
                    placeholder="email@example.com / +7..."
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
