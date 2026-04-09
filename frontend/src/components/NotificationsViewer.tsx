import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckSquare, MessageSquare, AlertCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead } from '@/api/tasks';

export const NotificationsViewer: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [isOpen, setIsOpen] = useState(false);

    // Auto-refresh notifications every 3 minutes
    const { data: notifications = [] } = useQuery({
        queryKey: ['notifications'],
        queryFn: fetchNotifications,
        refetchInterval: 3 * 60 * 1000,
    });

    const unreadCount = notifications.filter(n => !n.is_read).length;
    // Show max 10 notifications in dropdown
    const topNotifications = notifications.slice(0, 10);

    const markReadMutation = useMutation({
        mutationFn: markNotificationRead,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
    });

    const markAllReadMutation = useMutation({
        mutationFn: markAllNotificationsRead,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
    });

    const handleNotificationClick = (notif: any) => {
        if (!notif.is_read) markReadMutation.mutate(notif.id);
        setIsOpen(false);
        if (notif.task) {
            navigate(`/tasks/${notif.task}`);
        }
    };

    return (
        <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative h-9 w-9">
                    <Bell className="h-5 w-5" />
                    {unreadCount > 0 && (
                        <span className="absolute top-1 right-1 h-2.5 w-2.5 rounded-full bg-red-500 border-2 border-background animate-pulse" />
                    )}
                </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-80 max-h-[85vh] overflow-y-auto">
                <div className="flex items-center justify-between px-2 py-2">
                    <DropdownMenuLabel className="p-0">Уведомления</DropdownMenuLabel>
                    {unreadCount > 0 && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-auto p-0 text-xs text-primary hover:bg-transparent hover:underline"
                            onClick={() => markAllReadMutation.mutate()}
                        >
                            Прочитать все
                        </Button>
                    )}
                </div>
                <DropdownMenuSeparator />

                {topNotifications.length === 0 ? (
                    <div className="py-6 text-center text-sm text-muted-foreground flex flex-col items-center gap-2">
                        <CheckSquare className="h-8 w-8 text-muted-foreground/30" />
                        <p>Нет новых уведомлений</p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-1 px-1 py-1">
                        {topNotifications.map(n => (
                            <DropdownMenuItem
                                key={n.id}
                                className={`flex flex-col items-start gap-1 p-3 cursor-pointer ${!n.is_read ? 'bg-primary/5 font-medium' : 'opacity-80'}`}
                                onClick={() => handleNotificationClick(n)}
                            >
                                <div className="flex items-center gap-2 w-full">
                                    {n.verb.includes('комментарий') ? <MessageSquare className="h-4 w-4 text-blue-500 shrink-0" /> : <AlertCircle className="h-4 w-4 text-orange-500 shrink-0" />}
                                    <span className="text-sm truncate w-full">
                                        <strong className="text-primary">{n.actor_name}</strong> {n.verb}
                                    </span>
                                    {!n.is_read && <span className="h-2 w-2 rounded-full bg-primary shrink-0 ml-auto" />}
                                </div>
                                {n.task_key && (
                                    <span className="text-xs text-muted-foreground ml-6">
                                        В задаче: {n.task_key}
                                    </span>
                                )}
                                <span className="text-[10px] text-muted-foreground/70 ml-6 uppercase">
                                    {new Date(n.created_at).toLocaleString('ru')}
                                </span>
                            </DropdownMenuItem>
                        ))}

                        {notifications.length > 10 && (
                            <div className="p-2 text-center text-xs text-muted-foreground">
                                Показаны последние 10
                            </div>
                        )}
                    </div>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};
