import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useEffect, useRef } from 'react';

type Props = {
    roles?: string[];
};

const isEditor = (roles?: string[]) => {
    if (!roles) return false;
    return roles.includes('editor') || roles.includes('staff');
}

export const ProfileSidebar: React.FC<Props> = ({ roles }) => {
    const editor = isEditor(roles);

    return (
        <aside className="bg-card rounded-lg border p-4">
            <h4 className="font-semibold mb-3">Account</h4>
            <ul className="space-y-2 text-sm">
                <li><Link to="/myprofile" className="text-primary hover:underline">My profile</Link></li>
                <li><Link to="/myprofile" className="hover:underline">Settings</Link></li>
            </ul>

            {editor && (
                <div className="mt-6">
                    <h4 className="font-semibold mb-3">Editor</h4>
                    <ul className="space-y-2 text-sm">
                        <li>
                            <Link to="/manage/news" className="text-primary hover:underline">Manage News</Link>
                        </li>
                        <li>
                            <Link to="/manage/projects" className="text-primary hover:underline">Manage Projects</Link>
                        </li>
                        <li>
                            <Link to="/manage/contacts" className="text-primary hover:underline flex items-center">
                                <span>Contact Requests</span>
                                {/* Fetch count of unhandled requests for staff/admin */}
                                <UnreadContactsBadge />
                            </Link>
                        </li>
                        <li>
                            <a href="/admin/" className="text-primary hover:underline">Django admin</a>
                        </li>
                    </ul>

                    <h4 className="font-semibold mb-3 mt-6">HR Management</h4>
                    <ul className="space-y-2 text-sm">
                        <li>
                            <Link to="/hr/employees" className="text-primary hover:underline">Employees</Link>
                        </li>
                        <li>
                            <Link to="/hr/departments" className="text-primary hover:underline">Departments</Link>
                        </li>
                        <li>
                            <Link to="/hr/positions" className="text-primary hover:underline">Positions</Link>
                        </li>
                        <li>
                            <Link to="/hr/time-tracking" className="text-primary hover:underline">Time Tracking</Link>
                        </li>
                        <li>
                            <Link to="/hr/vacancies" className="text-primary hover:underline">Vacancies</Link>
                        </li>
                        <li>
                            <Link to="/hr/applications" className="text-primary hover:underline">Applications</Link>
                        </li>
                        <li>
                            <Link to="/hr/documents" className="text-primary hover:underline">Documents</Link>
                        </li>
                        <li>
                            <Link to="/hr/logs" className="text-primary hover:underline">Action Logs</Link>
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
