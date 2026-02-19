import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from 'react-i18next';

import { UserProfile } from '../../types/userProfile';

type Props = {
    roles?: string[];
    department?: string;
    position?: string;
};

const isEditor = (roles?: string[]) => {
    if (!roles) return false;
    return roles.includes('editors') || roles.includes('staff');
}

const isHRManager = (roles?: string[]) => {
    if (!roles) return false;
    return (
        roles.includes('hr_manager')
        || roles.includes('senior_hr')
        || roles.includes('junior_hr')
        || roles.includes('senior_manager')
        || roles.includes('junior_manager')
        || roles.includes('staff')
    );
}

const isAdmin = (roles?: string[]) => {
    if (!roles) return false;
    return roles.includes('staff');
}

export const ProfileSidebar: React.FC<Props> = ({ roles, department, position }) => {
    const { t } = useTranslation();
    const editor = isEditor(roles);
    const hrManager = isHRManager(roles);
    const admin = isAdmin(roles);
    const hasTasksAccess = hrManager || (department && position);

    return (
        <aside className="bg-card rounded-lg border p-4">
            <h4 className="font-semibold mb-3">{t('profile.sidebar.account')}</h4>
            <ul className="space-y-2 text-sm">
                <li><Link to="/myprofile" className="text-primary hover:underline">{t('profile.sidebar.myProfile')}</Link></li>
                <li><Link to="/myprofile" className="hover:underline">{t('profile.sidebar.settings')}</Link></li>
            </ul>

            {editor && (
                <div className="mt-6">
                    <h4 className="font-semibold mb-3">{t('profile.sidebar.editor')}</h4>
                    <ul className="space-y-2 text-sm">
                        <li>
                            <Link to="/manage/news" className="text-primary hover:underline">{t('profile.sidebar.manageNews')}</Link>
                        </li>
                        <li>
                            <Link to="/manage/projects" className="text-primary hover:underline">{t('profile.sidebar.manageProjects')}</Link>
                        </li>
                        <li>
                            <Link to="/manage/contacts" className="text-primary hover:underline flex items-center">
                                <span>{t('profile.sidebar.contactRequests')}</span>
                                {/* Fetch count of unhandled requests for staff/admin */}
                                <UnreadContactsBadge />
                            </Link>
                        </li>
                    </ul>
                </div>
            )}

            {hrManager && (
                <div className="mt-6">
                    <h4 className="font-semibold mb-3">{t('profile.sidebar.hrManagement')}</h4>
                    <ul className="space-y-2 text-sm">
                        <li>
                            <Link to="/hr/employees" className="text-primary hover:underline">{t('profile.sidebar.employees')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/departments" className="text-primary hover:underline">{t('profile.sidebar.departments')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/positions" className="text-primary hover:underline">{t('profile.sidebar.positions')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/time-tracking" className="text-primary hover:underline">{t('profile.sidebar.timeTracking')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/vacancies" className="text-primary hover:underline">{t('profile.sidebar.vacancies')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/applications" className="text-primary hover:underline">{t('profile.sidebar.applications')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/documents" className="text-primary hover:underline">{t('profile.sidebar.documents')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/profiles" className="text-primary hover:underline">{t('profile.sidebar.profiles')}</Link>
                        </li>
                        <li>
                            <Link to="/hr/history" className="text-primary hover:underline">{t('profile.sidebar.history')}</Link>
                        </li>
                    </ul>
                </div>
            )}

            {hasTasksAccess && (
                <div className="mt-6">
                    <h4 className="font-semibold mb-3">{t('profile.sidebar.tasks')}</h4>
                    <ul className="space-y-2 text-sm">
                        <li>
                            <Link to="/tasks" className="text-primary hover:underline">{t('profile.sidebar.tasksList')}</Link>
                        </li>
                        <li>
                            <Link to="/tasks/roadmap" className="text-primary hover:underline">{t('profile.sidebar.roadmap')}</Link>
                        </li>
                        <li>
                            <Link to="/tasks/reports" className="text-primary hover:underline">{t('profile.sidebar.reports')}</Link>
                        </li>
                    </ul>
                </div>
            )}

            {admin && (
                <div className="mt-6">
                    <h4 className="font-semibold mb-3">{t('profile.sidebar.adminTools')}</h4>
                    <ul className="space-y-2 text-sm">
                        <li>
                            <a href="/admin/" className="text-primary hover:underline">{t('profile.sidebar.djangoAdmin')}</a>
                        </li>
                        <li>
                            <Link to="/admin/registrations" className="text-primary hover:underline flex items-center">
                                <span>{t('profile.sidebar.registrations')}</span>
                                <PendingRegistrationsBadge />
                            </Link>
                        </li>
                        <li>
                            <Link to="/hr/logs" className="text-primary hover:underline">{t('profile.sidebar.actionLogs')}</Link>
                        </li>
                    </ul>
                </div>
            )}
        </aside>
    );
}

export default ProfileSidebar;

const UnreadContactsBadge: React.FC = () => {
    const { data, error } = useQuery({
        queryKey: ['contact-requests-stats'],
        queryFn: async () => {
            const res = await api.get('v1/contact-requests/stats/');
            return res.data;
        },
        retry: false,
        refetchInterval: 30000,
    });

    if (error) return null;
    const count = data?.unhandled ?? 0;
    if (!count) return null;
    return <Badge className="ml-2">{count}</Badge>;
};

const PendingRegistrationsBadge: React.FC = () => {
    const { data, error } = useQuery({
        queryKey: ['pending-registrations-count'],
        queryFn: async () => {
            const res = await api.get('v1/admin/pending-registrations/');
            return res.data;
        },
        retry: false,
        refetchInterval: 30000,
    });

    if (error) return null;
    const count = Array.isArray(data) ? data.length : 0;
    if (!count) return null;
    return <Badge variant="destructive" className="ml-2">{count}</Badge>;
};
