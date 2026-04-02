import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

import { createTask, fetchVersions } from '@/api/tasks';
import { fetchDepartments, fetchEmployeeUsers } from '@/api/hr';
import type { Task, TaskPriority, TaskType } from '@/types/tasks';

const PRIORITY_CONFIG: Record<TaskPriority, { color: string; icon: string }> = {
    critical: { color: 'bg-red-500 text-white', icon: '🔴' },
    high: { color: 'bg-orange-500 text-white', icon: '🟠' },
    medium: { color: 'bg-yellow-500 text-black', icon: '🟡' },
    low: { color: 'bg-blue-500 text-white', icon: '🔵' },
    trivial: { color: 'bg-gray-400 text-white', icon: '⚪' },
};

const TYPE_KEYS: TaskType[] = ['task', 'bug', 'story', 'epic', 'subtask'];

export interface CreateTaskModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    defaultParent?: number;
    defaultVersion?: number;
    defaultAssignee?: number;
    defaultDepartment?: number;
}

export const CreateTaskModal: React.FC<CreateTaskModalProps> = ({
    open, onOpenChange, defaultParent, defaultVersion, defaultAssignee, defaultDepartment
}) => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    const [form, setForm] = useState({
        summary: '', description: '', task_type: 'task' as TaskType,
        priority: 'medium' as TaskPriority,
        assignee: defaultAssignee ? String(defaultAssignee) : '',
        department: defaultDepartment ? String(defaultDepartment) : '',
        version: defaultVersion ? String(defaultVersion) : '',
        parent: defaultParent || undefined,
        due_date: '', start_date: '',
    });

    useEffect(() => {
        if (open) {
            setForm(prev => ({
                ...prev,
                parent: defaultParent || prev.parent,
                assignee: defaultAssignee ? String(defaultAssignee) : prev.assignee,
                department: defaultDepartment ? String(defaultDepartment) : prev.department,
                version: defaultVersion ? String(defaultVersion) : prev.version,
                task_type: defaultParent ? 'subtask' : prev.task_type
            }));
        }
    }, [open, defaultParent, defaultAssignee, defaultDepartment, defaultVersion]);

    const { data: departments = [] } = useQuery({ queryKey: ['hr-departments'], queryFn: fetchDepartments, enabled: open });
    const { data: versions = [] } = useQuery({ queryKey: ['hr-versions'], queryFn: () => fetchVersions(), enabled: open });
    const { data: users = [] } = useQuery({ queryKey: ['hr-users'], queryFn: () => fetchEmployeeUsers(), enabled: open });

    const createMutation = useMutation({
        mutationFn: (data: Partial<Task>) => createTask(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['hr-tasks'] });
            if (defaultParent) {
                queryClient.invalidateQueries({ queryKey: ['hr-task', String(defaultParent)] });
            }
            onOpenChange(false);
            setForm({
                summary: '', description: '', task_type: 'task', priority: 'medium',
                assignee: '', department: '', version: '', due_date: '', start_date: '', parent: undefined
            });
            toast.success(t('tasks.pages.list.createDialog.success', 'Задача успешно создана'));
        },
        onError: () => toast.error(t('tasks.pages.list.createDialog.error', 'Ошибка при создании задачи')),
    });

    function handleCreate() {
        if (!form.summary.trim()) {
            toast.error(t('tasks.pages.list.createDialog.summaryRequired', 'Заголовок обязателен'));
            return;
        }
        const payload: Record<string, any> = {
            summary: form.summary,
            description: form.description,
            task_type: form.task_type,
            priority: form.priority,
        };
        if (form.assignee) payload.assignee = Number(form.assignee);
        if (form.department) payload.department = Number(form.department);
        if (form.version) payload.version = Number(form.version);
        if (form.parent) payload.parent = form.parent;
        if (form.due_date) payload.due_date = form.due_date;
        if (form.start_date) payload.start_date = form.start_date;

        createMutation.mutate(payload);
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto z-[100]">
                <DialogHeader>
                    <DialogTitle>{t('tasks.pages.list.createDialog.title', 'Создать задачу')}</DialogTitle>
                </DialogHeader>

                <div className="grid gap-4 py-2">
                    <div>
                        <Label>{t('tasks.pages.list.createDialog.summary', 'Заголовок')}</Label>
                        <Input
                            value={form.summary}
                            onChange={(e) => setForm({ ...form, summary: e.target.value })}
                            placeholder={t('tasks.pages.list.createDialog.summaryPlaceholder', 'Короткое и понятное название')}
                            autoFocus
                        />
                    </div>

                    <div>
                        <Label>{t('tasks.pages.list.createDialog.description', 'Описание')}</Label>
                        <Textarea
                            value={form.description}
                            onChange={(e) => setForm({ ...form, description: e.target.value })}
                            placeholder={t('tasks.pages.list.createDialog.descriptionPlaceholder', 'Подробное описание задачи...')}
                            rows={4}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>{t('tasks.pages.list.createDialog.type', 'Тип задачи')}</Label>
                            <Select
                                value={form.task_type}
                                onValueChange={(v) => setForm({ ...form, task_type: v as TaskType })}
                                disabled={!!defaultParent} // Subtasks forced to subtask type
                            >
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {TYPE_KEYS.map((k) => (
                                        <SelectItem key={k} value={k}>{t(`tasks.pages.list.type.${k}`, k)}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>{t('tasks.pages.list.createDialog.priority', 'Приоритет')}</Label>
                            <Select
                                value={form.priority}
                                onValueChange={(v) => setForm({ ...form, priority: v as TaskPriority })}
                            >
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                                        <SelectItem key={k} value={k}>{v.icon} {t(`tasks.pages.list.priority.${k}`, k)}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>{t('tasks.pages.list.createDialog.assignee', 'Исполнитель')}</Label>
                            <Select value={form.assignee} onValueChange={(v) => setForm({ ...form, assignee: v })}>
                                <SelectTrigger><SelectValue placeholder={t('tasks.pages.list.createDialog.selectPlaceholder', 'Не назначен')} /></SelectTrigger>
                                <SelectContent>
                                    {users.map((u) => (
                                        <SelectItem key={u.id} value={String(u.id)}>
                                            {u.full_name || u.username}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>{t('tasks.pages.list.createDialog.department', 'Отдел')}</Label>
                            <Select value={form.department} onValueChange={(v) => setForm({ ...form, department: v })}>
                                <SelectTrigger><SelectValue placeholder={t('tasks.pages.list.createDialog.selectPlaceholder', 'Не указан')} /></SelectTrigger>
                                <SelectContent>
                                    {departments.map((d) => (
                                        <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label>{t('tasks.pages.list.createDialog.version', 'Версия/Релиз')}</Label>
                            <Select value={form.version} onValueChange={(v) => setForm({ ...form, version: v })}>
                                <SelectTrigger><SelectValue placeholder={t('tasks.pages.list.createDialog.selectPlaceholder', 'Не привязан')} /></SelectTrigger>
                                <SelectContent>
                                    {versions.map((v) => (
                                        <SelectItem key={v.id} value={String(v.id)}>{v.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>{t('tasks.pages.list.createDialog.dueDate', 'Дедлайн')}</Label>
                            <Input
                                type="date"
                                value={form.due_date}
                                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="grid grid-rows-[auto] gap-4">
                        <div>
                            <Label>{t('tasks.pages.list.createDialog.startDate', 'Дата начала')}</Label>
                            <Input
                                type="date"
                                value={form.start_date}
                                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                            />
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        {t('tasks.pages.list.createDialog.cancel', 'Отмена')}
                    </Button>
                    <Button onClick={handleCreate} disabled={createMutation.isPending}>
                        {createMutation.isPending ? t('tasks.pages.list.createDialog.submitting', 'Создание...') : t('tasks.pages.list.createDialog.submit', 'Создать')}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
