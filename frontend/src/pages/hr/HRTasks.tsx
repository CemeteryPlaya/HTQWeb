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
  Bug, BookOpen, Layers, CheckSquare, ListTodo,
} from 'lucide-react';
import {
  fetchTasks, createTask, deleteTask,
  fetchLabels, fetchVersions,
} from '@/api/tasks';
import { fetchDepartments, fetchEmployeeUsers } from '@/api/hr';
import type { Task, TaskPriority, TaskStatus, TaskType } from '@/types/tasks';

/* ---- Constants ---- */

const PRIORITY_CONFIG: Record<TaskPriority, { label: string; color: string; icon: string }> = {
  critical: { label: 'Критический', color: 'bg-red-500 text-white', icon: '🔴' },
  high:     { label: 'Высокий',     color: 'bg-orange-500 text-white', icon: '🟠' },
  medium:   { label: 'Средний',     color: 'bg-yellow-500 text-black', icon: '🟡' },
  low:      { label: 'Низкий',      color: 'bg-blue-500 text-white', icon: '🔵' },
  trivial:  { label: 'Тривиальный', color: 'bg-gray-400 text-white', icon: '⚪' },
};

const STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  open:        { label: 'Открыта',   color: 'bg-slate-500 text-white' },
  in_progress: { label: 'В работе',  color: 'bg-blue-600 text-white' },
  in_review:   { label: 'На ревью',  color: 'bg-purple-500 text-white' },
  done:        { label: 'Готова',     color: 'bg-green-500 text-white' },
  closed:      { label: 'Закрыта',   color: 'bg-gray-600 text-white' },
};

const TYPE_ICONS: Record<TaskType, React.ReactNode> = {
  task:    <CheckSquare className="h-4 w-4 text-blue-500" />,
  bug:     <Bug className="h-4 w-4 text-red-500" />,
  story:   <BookOpen className="h-4 w-4 text-green-500" />,
  epic:    <Layers className="h-4 w-4 text-purple-500" />,
  subtask: <ListTodo className="h-4 w-4 text-gray-500" />,
};

const TYPE_LABELS: Record<TaskType, string> = {
  task: 'Задача', bug: 'Баг', story: 'История', epic: 'Эпик', subtask: 'Подзадача',
};

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

  const createMutation = useMutation({
    mutationFn: (data: Partial<Task>) => createTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-tasks'] });
      setCreateOpen(false);
      resetForm();
      toast.success('Задача создана');
    },
    onError: () => toast.error('Ошибка при создании задачи'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-tasks'] });
      toast.success('Задача удалена');
    },
    onError: () => toast.error('Ошибка при удалении задачи'),
  });

  function resetForm() {
    setForm({
      summary: '', description: '', task_type: 'task',
      priority: 'medium', assignee: '', department: '',
      version: '', due_date: '', start_date: '',
    });
  }

  function handleCreate() {
    if (!form.summary.trim()) {
      toast.error('Заголовок обязателен');
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
    if (form.due_date) payload.due_date = form.due_date;
    if (form.start_date) payload.start_date = form.start_date;
    createMutation.mutate(payload);
  }

  return (
    <TasksLayout title="Задачи" subtitle="Управление задачами — аналог Jira">
      {/* Toolbar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Поиск по ключу, заголовку..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Статус" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Приоритет" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все приоритеты</SelectItem>
                {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v.icon} {v.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Filter className="h-4 w-4 mr-1" /> Фильтры
            </Button>

            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> Создать задачу
            </Button>
          </div>

          {/* Extended filters */}
          {showFilters && (
            <div className="mt-4 flex flex-wrap gap-3 border-t pt-4">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Тип" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все типы</SelectItem>
                  {Object.entries(TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Отдел" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все отделы</SelectItem>
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
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Задачи ({tasks.length})</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Загрузка...</div>
          ) : error ? (
            <div className="flex items-center gap-2 text-red-500 py-8 justify-center">
              <AlertCircle className="h-5 w-5" />
              Ошибка загрузки задач
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Задач не найдено. Создайте первую задачу!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[100px]">Тип</TableHead>
                    <TableHead className="w-[110px]">Ключ</TableHead>
                    <TableHead>Заголовок</TableHead>
                    <TableHead className="w-[120px]">Статус</TableHead>
                    <TableHead className="w-[120px]">Приоритет</TableHead>
                    <TableHead className="w-[150px]">Исполнитель</TableHead>
                    <TableHead className="w-[150px]">Отдел</TableHead>
                    <TableHead className="w-[100px]">Срок</TableHead>
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
                            {TYPE_LABELS[task.task_type]}
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
                          {STATUS_CONFIG[task.status]?.label || task.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">
                          {PRIORITY_CONFIG[task.priority]?.icon}{' '}
                          {PRIORITY_CONFIG[task.priority]?.label || task.priority}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        {task.assignee_name || '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {task.department_name || '—'}
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

      {/* Create Task Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Создать задачу</DialogTitle>
          </DialogHeader>

          <div className="grid gap-4 py-2">
            <div>
              <Label>Заголовок *</Label>
              <Input
                value={form.summary}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
                placeholder="Краткое описание задачи"
              />
            </div>

            <div>
              <Label>Описание</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Подробное описание..."
                rows={4}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Тип</Label>
                <Select
                  value={form.task_type}
                  onValueChange={(v) => setForm({ ...form, task_type: v as TaskType })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(TYPE_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Приоритет</Label>
                <Select
                  value={form.priority}
                  onValueChange={(v) => setForm({ ...form, priority: v as TaskPriority })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.icon} {v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Исполнитель</Label>
                <Select value={form.assignee} onValueChange={(v) => setForm({ ...form, assignee: v })}>
                  <SelectTrigger><SelectValue placeholder="Выберите..." /></SelectTrigger>
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
                <Label>Отдел</Label>
                <Select value={form.department} onValueChange={(v) => setForm({ ...form, department: v })}>
                  <SelectTrigger><SelectValue placeholder="Выберите..." /></SelectTrigger>
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
                <Label>Версия / Релиз</Label>
                <Select value={form.version} onValueChange={(v) => setForm({ ...form, version: v })}>
                  <SelectTrigger><SelectValue placeholder="Выберите..." /></SelectTrigger>
                  <SelectContent>
                    {versions.map((v) => (
                      <SelectItem key={v.id} value={String(v.id)}>{v.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Срок</Label>
                <Input
                  type="date"
                  value={form.due_date}
                  onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                />
              </div>
            </div>

            <div>
              <Label>Дата начала</Label>
              <Input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Отмена
            </Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Создание...' : 'Создать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </TasksLayout>
  );
};

export default HRTasks;
