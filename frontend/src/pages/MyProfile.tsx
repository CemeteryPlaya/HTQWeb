import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from "sonner";
import { useTranslation } from 'react-i18next';
import api from '../api/client';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { ProfileHeader } from '../components/profile/ProfileHeader';
import ProfileSidebar from '../components/profile/ProfileSidebar';
import { ProfileForm } from '../components/profile/ProfileForm';
import { ProfileAvatar } from '../components/profile/ProfileAvatar';
import { CalendarWidget } from '../components/calendar/CalendarWidget';
import { UserProfile, ProfileFormData } from '../types/userProfile';
import {
    clearAuthStorage,
    readCachedProfile,
    writeCachedProfile,
} from '@/lib/auth/profileStorage';

const MyProfile = () => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    const { data: serverProfile, isLoading, error } = useQuery({
        queryKey: ['profile'],
        queryFn: async () => {
            const res = await api.get<UserProfile>('users/v1/profile/me');
            writeCachedProfile(res.data);
            return res.data;
        }
    });

    const profile = serverProfile || readCachedProfile();

    const updateProfileMutation = useMutation({
        mutationFn: async (data: Partial<UserProfile> & { avatar?: File }) => {
            const formData = new FormData();

            if (data.display_name !== undefined) formData.append('display_name', data.display_name);
            if (data.firstName !== undefined) formData.append('firstName', data.firstName);
            if (data.lastName !== undefined) formData.append('lastName', data.lastName);
            if (data.patronymic !== undefined) formData.append('patronymic', data.patronymic);
            if (data.phone !== undefined) formData.append('phone', data.phone);
            if (data.bio !== undefined) formData.append('bio', data.bio);
            if (data.settings) formData.append('settings', JSON.stringify(data.settings));
            if (data.avatar) formData.append('avatar', data.avatar);

            const res = await api.patch<UserProfile>('users/v1/profile/me', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return res.data;
        },
        onSuccess: (updatedProfile) => {
            queryClient.setQueryData(['profile'], updatedProfile);
            toast.success(t('profile.updated'));
        },
        onError: (err) => {
            console.error(err);
            toast.error("Failed to update profile");
        }
    });

    const handleFormSubmit = (data: ProfileFormData) => {
        const { avatar, ...rest } = data;
        updateProfileMutation.mutate(rest);
    };

    const handleAvatarChange = (file: File) => {
        updateProfileMutation.mutate({ avatar: file });
    };

    const handleLogout = async () => {
        clearAuthStorage();

        // Clear axios default header if client exists
        try {
            const client = await api.getClient();
            if (client && client.defaults && client.defaults.headers) {
                delete client.defaults.headers.common['Authorization'];
            }
        } catch (e) {
            // ignore
        }

        // Clear cached profile data
        queryClient.clear();

        // Redirect to login
        navigate('/login');
    };

    if (isLoading && !profile) return <div className="min-h-screen flex items-center justify-center">{t('profile.loading')}</div>;
    if (error && !profile) return <div className="min-h-screen flex items-center justify-center text-red-500">{t('profile.error')}</div>;

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Header />
            <main className="flex-1 container mx-auto px-4 py-8">
                <h1 className="text-3xl font-bold mb-6">{t('profile.title')}</h1>

                {profile && (
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                        <div className="lg:col-span-1">
                            <ProfileSidebar
                                roles={profile.roles}
                                department={profile.department}
                                position={profile.position}
                            />
                        </div>

                        <div className="lg:col-span-3 space-y-6">
                            <div className="bg-card rounded-lg border p-6 flex flex-col items-center">
                                <ProfileAvatar
                                    avatarUrl={profile.avatarUrl}
                                    firstName={profile.fio || profile.displayName || profile.firstName}
                                    onAvatarChange={handleAvatarChange}
                                />
                                <div className="mt-4 text-center">
                                    <h3 className="font-bold text-lg">{profile.fio || profile.display_name}</h3>
                                    <p className="text-sm text-muted-foreground">{profile.email}</p>
                                    <p className="text-sm text-muted-foreground mt-2">{t('profile.rolesLabel')}: {profile.roles?.join(', ') || t('profile.rolesNone')}</p>
                                    <p className="text-sm text-muted-foreground">{t('profile.staffLabel')}: {profile.user?.is_staff ? t('profile.yes') : (profile.roles?.includes('staff') ? t('profile.yes') : t('profile.no'))}</p>
                                    <button onClick={handleLogout} className="mt-4 inline-block w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded">
                                        {t('profile.logout')}
                                    </button>
                                </div>
                            </div>

                            <ProfileHeader profile={profile} />

                            <div className="bg-card rounded-3xl border p-6 shadow-sm overflow-hidden">
                                <h3 className="text-xl font-bold mb-4 px-2">{t('hr.calendar.title')}</h3>
                                <CalendarWidget compact initialView="month" />
                            </div>
                        </div>
                    </div>
                )}
            </main>
            <Footer />
        </div>
    );
};

export default MyProfile;
