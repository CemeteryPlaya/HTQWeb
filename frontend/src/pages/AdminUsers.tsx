import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import api from '../api/client';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface AdminUser {
    id: number;
    username: string;
    email: string;
    is_staff: boolean;
    is_active: boolean;
    date_joined: string;
}

const AdminUsers = () => {
    const { t } = useTranslation();
    const { data: users, isLoading, error } = useQuery({
        queryKey: ['admin-users'],
        queryFn: async () => {
            const res = await api.get<AdminUser[]>('users/v1/admin/users/');
            return res.data;
        }
    });

    if (isLoading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    if (error) return (
        <div className="min-h-screen bg-background flex flex-col">
            <Header />
            <main className="flex-1 container mx-auto px-4 py-8 flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-red-500 mb-2">Access Denied</h1>
                    <p>You do not have permission to view this page.</p>
                </div>
            </main>
            <Footer />
        </div>
    );

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Header />
            <main className="flex-1 container mx-auto px-4 py-8">
                <div className="mb-6 flex flex-col gap-4">
                    <Link
                        to="/myprofile"
                        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        {t('hr.backToMain', 'Назад в профиль')}
                    </Link>
                    <h1 className="text-3xl font-bold">{t('admin.users.title')}</h1>
                </div>
                <div className="bg-card rounded-lg border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>{t('admin.users.username')}</TableHead>
                                <TableHead>{t('admin.users.email')}</TableHead>
                                <TableHead>{t('admin.users.joined')}</TableHead>
                                <TableHead>{t('admin.users.status')}</TableHead>
                                <TableHead>{t('admin.users.role')}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {users?.map((user) => (
                                <TableRow key={user.id}>
                                    <TableCell className="font-medium">{user.username}</TableCell>
                                    <TableCell>{user.email}</TableCell>
                                    <TableCell>{new Date(user.date_joined).toLocaleDateString()}</TableCell>
                                    <TableCell>
                                        <Badge variant={user.is_active ? "default" : "secondary"}>
                                            {user.is_active ? t('admin.users.active') : t('admin.users.inactive')}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant={user.is_staff ? "destructive" : "outline"}>
                                            {user.is_staff ? t('admin.users.admin') : t('admin.users.user')}
                                        </Badge>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </main>
            <Footer />
        </div>
    );
};

export default AdminUsers;
