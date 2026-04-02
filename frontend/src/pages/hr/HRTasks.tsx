import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { TasksLayout } from '@/components/tasks/TasksLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import {
  Plus, Search, Filter, AlertCircle, ArrowUpDown,
  Bug, BookOpen, Layers, CheckSquare, ListTodo, Edit, Trash2
} from 'lucide-react';
import {
  fetchTasks, createTask, deleteTask, updateTask,
  fetchLabels, fetchVersions,
} from '@/api/tasks';
import { fetchDepartments, fetchEmployeeUsers } from '@/api/hr';
import api from '@/api/client';
import { KanbanBoard } from '@/components/tasks/KanbanBoard';
import { CreateTaskModal } from '@/components/tasks/CreateTaskModal';
import type { Task, TaskPriority, TaskStatus, TaskType } from '@/types/tasks';
import type { UserProfile } from '@/types/userProfile';

/* ---- Constants ---- */

const PRIORITY_CONFIG: Record<TaskPriority, { color: string; icon: string }> = {
  critical: { color: 'bg-red-500 text-white', icon: '🔴' },
  high: { color: 'bg-orange-500 text-white', icon: '🟠' },
  medium: { color: 'bg-yellow-500 text-black', icon: '🟡' },
  low: { color: 'bg-blue-500 text-white', icon: '🔵' },
  trivial: { color: 'bg-gray-400 text-white', icon: '⚪' },
};

const STATUS_CONFIG: Record<TaskStatus, { color: string }> = {
  open: { color: 'bg-slate-500 text-white' },
  in_progress: { color: 'bg-blue-600 text-white' },
  in_review: { color: 'bg-purple-500 text-white' },
  done: { color: 'bg-green-500 text-white' },
  closed: { color: 'bg-gray-600 text-white' },
};

const TYPE_ICONS: Record<TaskType, React.ReactNode> = {
  task: <CheckSquare className="h-4 w-4 text-blue-500" />,
  bug: <Bug className="h-4 w-4 text-red-500" />,
  story: <BookOpen className="h-4 w-4 text-green-500" />,
  epic: <Layers className="h-4 w-4 text-purple-500" />,
  subtask: <ListTodo className="h-4 w-4 text-gray-500" />,
};

const TYPE_KEYS: TaskType[] = ['task', 'bug', 'story', 'epic', 'subtask'];

/* ---- Component ---- */

const HRTasks: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  /* filters */
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [departmentFilter, setDepartmentFilter] = useState<string>('all');
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'board'>('board');

  /* create dialog */
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({
    summary: '', description: '', task_type: 'task' as TaskType,
    priority: 'medium' as TaskPriority, assignee: '' as string,
    department: '' as string, version: '' as string,
    due_date: '', start_date: '',
  });

  /* queries */
  const params: Record<string, string> = {};
  if (search) params.search = search;
  if (statusFilter !== 'all') params.status = statusFilter;
  if (priorityFilter !== 'all') params.priority = priorityFilter;
  if (typeFilter !== 'all') params.task_type = typeFilter;
  if (departmentFilter !== 'all') params.department = departmentFilter;

  const { data: tasks = [], isLoading, error } = useQuery({
    queryKey: ['hr-tasks', params],
    queryFn: () => fetchTasks(params),
  });

  const { data: departments = [] } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: fetchDepartments,
  });

  const { data: versions = [] } = useQuery({
    queryKey: ['hr-versions'],
    queryFn: () => fetchVersions(),
  });

  const { data: users = [] } = useQuery({
    queryKey: ['hr-users'],
    queryFn: () => fetchEmployeeUsers(),
  });

  const { data: labels = [] } = useQuery({
    queryKey: ['hr-labels'],
    queryFn: fetchLabels,
  });

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const res = await api.get<UserProfile>('v1/profile/me/');
      return res.data;
    }
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: TaskStatus }) => updateTask(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-tasks'] });
      toast.success(t('tasks.pages.list.statusUpdated', 'Статус обновлен'));
    },
    onError: () => toast.error(t('tasks.pages.list.statusError', 'Ошибка обновления статуса')),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-tasks'] });
      toast.success(t('tasks.pages.list.createDialog.success'));
    },
    onError: () => toast.error(t('tasks.pages.list.createDialog.error')),
  });

  return (
    <TasksLayout title={t('tasks.pages.list.title')} subtitle={t('tasks.pages.list.subtitle')}>
      {/* Toolbar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('tasks.pages.list.search')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder={t('tasks.pages.list.table.status')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('tasks.pages.list.allStatuses')}</SelectItem>
                {Object.keys(STATUS_CONFIG).map((k) => (
                  <SelectItem key={k} value={k}>{t(`tasks.pages.list.status.${k}`)}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder={t('tasks.pages.list.table.priority')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('tasks.pages.list.allPriorities')}</SelectItem>
                {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v.icon} {t(`tasks.pages.list.priority.${k}`)}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button variant={showFilters ? 'default' : 'outline'} size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Filter className="h-4 w-4" />
            </Button>

            <div className="flex bg-muted/50 p-1 rounded-md ml-auto gap-1 border">
              <Button
                variant={viewMode === 'board' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setViewMode('board')}
              >
                Kanban
              </Button>
              <Button
                variant={viewMode === 'table' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setViewMode('table')}
              >
                Table
              </Button>
            </div>

            <Button onClick={() => setCreateOpen(true)} size="sm">
              <Plus className="h-4 w-4 mr-1" /> {t('tasks.pages.list.create')}
            </Button>
          </div>

          {/* Extended filters */}
          {showFilters && (
            <div className="mt-4 flex flex-wrap gap-3 border-t pt-4">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder={t('tasks.pages.list.table.type')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('tasks.pages.list.allTypes')}</SelectItem>
                  {TYPE_KEYS.map((k) => (
                    <SelectItem key={k} value={k}>{t(`tasks.pages.list.type.${k}`)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder={t('tasks.pages.list.table.department')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('tasks.pages.list.allDepartments')}</SelectItem>
                  {departments.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Task list */}
      <Card className="flex-1 w-full min-w-0 overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>{t('tasks.pages.list.title')} ({tasks.length})</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="w-full min-w-0">
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">{t('tasks.pages.list.loading')}</div>
          ) : error ? (
            <div className="flex items-center gap-2 text-red-500 py-8 justify-center">
              <AlertCircle className="h-5 w-5" />
              {t('tasks.pages.list.error')}
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t('tasks.pages.list.empty')}
            </div>
          ) : viewMode === 'board' ? (
            <div className="-mx-2 -mb-2 w-full min-w-0 overflow-hidden">
              <KanbanBoard
                tasks={tasks}
                onStatusChange={(taskId, newStatus) => updateStatusMutation.mutate({ id: taskId, status: newStatus })}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">{t('tasks.pages.list.table.type')}</TableHead>
                    <TableHead className="w-[110px]">{t('tasks.pages.list.table.key')}</TableHead>
                    <TableHead>{t('tasks.pages.list.table.summary')}</TableHead>
                    <TableHead className="w-[120px]">{t('tasks.pages.list.table.status')}</TableHead>
                    <TableHead className="w-[120px]">{t('tasks.pages.list.table.priority')}</TableHead>
                    <TableHead className="w-[150px]">{t('tasks.pages.list.table.assignee')}</TableHead>
                    <TableHead className="w-[150px]">{t('tasks.pages.list.table.department')}</TableHead>
                    <TableHead className="w-[80px] text-center"></TableHead>
                    <TableHead className="w-[100px]">{t('tasks.pages.list.table.dueDate')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tasks.map((task) => (
                    <TableRow
                      key={task.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/tasks/${task.id}`)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {TYPE_ICONS[task.task_type]}
                          <span className="text-xs text-muted-foreground">
                            {t(`tasks.pages.list.type.${task.task_type}`)}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-sm font-medium text-primary">
                          {task.key}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{task.summary}</div>
                          {task.labels && task.labels.length > 0 && (
                            <div className="flex gap-1 mt-1">
                              {task.labels.map((l) => (
                                <Badge
                                  key={l.id}
                                  variant="outline"
                                  className="text-xs px-1.5 py-0"
                                  style={{ borderColor: l.color, color: l.color }}
                                >
                                  {l.name}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={STATUS_CONFIG[task.status]?.color || ''}>
                          {t(`tasks.pages.list.status.${task.status}`) || task.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">
                          {PRIORITY_CONFIG[task.priority]?.icon}{' '}
                          {t(`tasks.pages.list.priority.${task.priority}`) || task.priority}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {task.assignee_name || '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {task.department_name || '—'}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-center gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7 text-muted-foreground hover:text-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/tasks/${task.id}`);
                            }}
                            title={t('common.edit', 'Редактировать')}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm(t('tasks.pages.list.deleteConfirm', 'Вы уверены, что хотите удалить задачу?'))) {
                                deleteMutation.mutate(task.id);
                              }
                            }}
                            title={t('common.delete', 'Удалить')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {task.due_date || '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Task Dialog using the new global component */}
      <CreateTaskModal open={createOpen} onOpenChange={setCreateOpen} />
    </TasksLayout>
  );
};

export default HRTasks;
