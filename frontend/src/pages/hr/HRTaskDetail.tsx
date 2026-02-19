import React, { useState, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TasksLayout } from '@/components/tasks/TasksLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import {
  ArrowLeft, Paperclip, MessageSquare, Send, Upload,
  Bug, BookOpen, Layers, CheckSquare, ListTodo,
  Calendar, User, Building2, Tag, Clock,
} from 'lucide-react';
import {
  fetchTask, updateTask, addTaskComment, addTaskAttachment,
  fetchLabels, fetchVersions,
} from '@/api/tasks';
import { fetchDepartments, fetchEmployeeUsers } from '@/api/hr';
import type {
  Task, TaskPriority, TaskStatus, TaskType,
  TaskComment as TComment,
} from '@/types/tasks';

/* ---- Config maps ---- */

const PRIORITY_CONFIG: Record<TaskPriority, { label: string; icon: string }> = {
  critical: { label: 'Критический', icon: '🔴' },
  high:     { label: 'Высокий',     icon: '🟠' },
  medium:   { label: 'Средний',     icon: '🟡' },
  low:      { label: 'Низкий',      icon: '🔵' },
  trivial:  { label: 'Тривиальный', icon: '⚪' },
};

const STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  open:        { label: 'Открыта',   color: 'bg-slate-500 text-white' },
  in_progress: { label: 'В работе',  color: 'bg-blue-600 text-white' },
  in_review:   { label: 'На ревью',  color: 'bg-purple-500 text-white' },
  done:        { label: 'Готова',     color: 'bg-green-500 text-white' },
  closed:      { label: 'Закрыта',   color: 'bg-gray-600 text-white' },
};

const TYPE_ICONS: Record<TaskType, React.ReactNode> = {
  task:    <CheckSquare className="h-5 w-5 text-blue-500" />,
  bug:     <Bug className="h-5 w-5 text-red-500" />,
  story:   <BookOpen className="h-5 w-5 text-green-500" />,
  epic:    <Layers className="h-5 w-5 text-purple-500" />,
  subtask: <ListTodo className="h-5 w-5 text-gray-500" />,
};

const TYPE_LABELS: Record<TaskType, string> = {
  task: 'Задача', bug: 'Баг', story: 'История', epic: 'Эпик', subtask: 'Подзадача',
};

/* ---- Component ---- */

const HRTaskDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [commentText, setCommentText] = useState('');
  const [editingField, setEditingField] = useState<string | null>(null);

  const taskId = Number(id);

  const { data: task, isLoading, error } = useQuery({
    queryKey: ['hr-task', taskId],
    queryFn: () => fetchTask(taskId),
    enabled: !!taskId,
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

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Task>) => updateTask(taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['hr-tasks'] });
      toast.success('Задача обновлена');
      setEditingField(null);
    },
    onError: () => toast.error('Ошибка обновления'),
  });

  const commentMutation = useMutation({
    mutationFn: (body: string) => addTaskComment(taskId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-task', taskId] });
      setCommentText('');
      toast.success('Комментарий добавлен');
    },
    onError: () => toast.error('Ошибка добавления комментария'),
  });

  const attachMutation = useMutation({
    mutationFn: (file: File) => addTaskAttachment(taskId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-task', taskId] });
      toast.success('Файл прикреплён');
    },
    onError: () => toast.error('Ошибка прикрепления файла'),
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) attachMutation.mutate(file);
  }

  if (isLoading) {
    return (
      <TasksLayout title="Загрузка...">
        <div className="text-center py-12 text-muted-foreground">Загрузка задачи...</div>
      </TasksLayout>
    );
  }

  if (error || !task) {
    return (
      <TasksLayout title="Ошибка">
        <div className="text-center py-12 text-red-500">Задача не найдена</div>
      </TasksLayout>
    );
  }

  return (
    <TasksLayout title={task.key} subtitle={task.summary}>
      {/* Back link */}
      <Button variant="ghost" size="sm" onClick={() => navigate('/tasks')} className="mb-2">
        <ArrowLeft className="h-4 w-4 mr-1" /> К списку задач
      </Button>

      {/* Jira-like split layout */}
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">

        {/* ===== LEFT: Content ===== */}
        <div className="space-y-6">

          {/* Header */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                {TYPE_ICONS[task.task_type]}
                <span className="font-mono text-lg font-bold text-primary">{task.key}</span>
                <Badge className={STATUS_CONFIG[task.status]?.color}>
                  {STATUS_CONFIG[task.status]?.label}
                </Badge>
              </div>
              <h2 className="text-2xl font-semibold mb-2">{task.summary}</h2>
            </CardContent>
          </Card>

          {/* Description */}
          <Card>
            <CardHeader><CardTitle>Описание</CardTitle></CardHeader>
            <CardContent>
              {editingField === 'description' ? (
                <div className="space-y-2">
                  <Textarea
                    defaultValue={task.description}
                    id="desc-edit"
                    rows={6}
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => {
                      const el = document.getElementById('desc-edit') as HTMLTextAreaElement;
                      updateMutation.mutate({ description: el.value });
                    }}>Сохранить</Button>
                    <Button size="sm" variant="outline" onClick={() => setEditingField(null)}>Отмена</Button>
                  </div>
                </div>
              ) : (
                <div
                  className="prose prose-sm dark:prose-invert cursor-pointer min-h-[40px] whitespace-pre-wrap"
                  onClick={() => setEditingField('description')}
                >
                  {task.description || <span className="text-muted-foreground italic">Нажмите, чтобы добавить описание...</span>}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Subtasks */}
          {task.subtasks && task.subtasks.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Подзадачи ({task.subtasks.length})</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {task.subtasks.map((sub) => (
                    <Link
                      key={sub.id}
                      to={`/tasks/${sub.id}`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted transition-colors"
                    >
                      {TYPE_ICONS[sub.task_type]}
                      <span className="font-mono text-sm text-primary">{sub.key}</span>
                      <span className="text-sm flex-1">{sub.summary}</span>
                      <Badge className={STATUS_CONFIG[sub.status]?.color} variant="secondary">
                        {STATUS_CONFIG[sub.status]?.label}
                      </Badge>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Attachments */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Paperclip className="h-4 w-4" />
                  Вложения ({task.attachments?.length || 0})
                </span>
                <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-4 w-4 mr-1" /> Прикрепить
                </Button>
                <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(!task.attachments || task.attachments.length === 0) ? (
                <p className="text-muted-foreground text-sm">Нет вложений</p>
              ) : (
                <div className="space-y-2">
                  {task.attachments.map((att) => (
                    <div key={att.id} className="flex items-center gap-3 p-2 rounded border">
                      <Paperclip className="h-4 w-4 text-muted-foreground" />
                      <a href={att.file} target="_blank" rel="noreferrer"
                        className="text-sm font-medium text-primary hover:underline flex-1">
                        {att.filename}
                      </a>
                      <span className="text-xs text-muted-foreground">
                        {att.uploaded_by_name} · {new Date(att.created_at).toLocaleDateString('ru')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Comments */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Комментарии ({task.comments?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {task.comments?.map((comment) => (
                  <div key={comment.id} className="border rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{comment.author_name || 'Аноним'}</span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(comment.created_at).toLocaleString('ru')}
                      </span>
                    </div>
                    <p className="text-sm whitespace-pre-wrap">{comment.body}</p>
                  </div>
                ))}

                <Separator />

                <div className="flex gap-2">
                  <Textarea
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder="Написать комментарий..."
                    rows={2}
                    className="flex-1"
                  />
                  <Button
                    size="sm"
                    disabled={!commentText.trim() || commentMutation.isPending}
                    onClick={() => commentMutation.mutate(commentText)}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ===== RIGHT: Details sidebar ===== */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-sm uppercase tracking-wider">Детали</CardTitle></CardHeader>
            <CardContent className="space-y-4">

              {/* Status */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase">Статус</Label>
                <Select
                  value={task.status}
                  onValueChange={(v) => updateMutation.mutate({ status: v as TaskStatus })}
                >
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Priority */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase">Приоритет</Label>
                <Select
                  value={task.priority}
                  onValueChange={(v) => updateMutation.mutate({ priority: v as TaskPriority })}
                >
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.icon} {v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              {/* Assignee */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                  <User className="h-3 w-3" /> Исполнитель
                </Label>
                <Select
                  value={task.assignee ? String(task.assignee) : 'none'}
                  onValueChange={(v) => updateMutation.mutate({
                    assignee: v === 'none' ? null : Number(v),
                  } as any)}
                >
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Не назначен</SelectItem>
                    {users.map((u) => (
                      <SelectItem key={u.id} value={String(u.id)}>
                        {u.full_name || u.username}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Reporter */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase">Автор</Label>
                <p className="text-sm mt-1">{task.reporter_name || '—'}</p>
              </div>

              <Separator />

              {/* Department */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                  <Building2 className="h-3 w-3" /> Отдел
                </Label>
                <Select
                  value={task.department ? String(task.department) : 'none'}
                  onValueChange={(v) => updateMutation.mutate({
                    department: v === 'none' ? null : Number(v),
                  } as any)}
                >
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Не указан</SelectItem>
                    {departments.map((d) => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Version */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                  <Tag className="h-3 w-3" /> Версия
                </Label>
                <Select
                  value={task.version ? String(task.version) : 'none'}
                  onValueChange={(v) => updateMutation.mutate({
                    version: v === 'none' ? null : Number(v),
                  } as any)}
                >
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Не указана</SelectItem>
                    {versions.map((v) => (
                      <SelectItem key={v.id} value={String(v.id)}>{v.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              {/* Labels */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase">Метки</Label>
                <div className="flex flex-wrap gap-1 mt-1">
                  {task.labels && task.labels.length > 0 ? task.labels.map((l) => (
                    <Badge
                      key={l.id}
                      variant="outline"
                      style={{ borderColor: l.color, color: l.color }}
                    >
                      {l.name}
                    </Badge>
                  )) : (
                    <span className="text-sm text-muted-foreground">Нет меток</span>
                  )}
                </div>
              </div>

              <Separator />

              {/* Dates */}
              <div>
                <Label className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> Дата начала
                </Label>
                <Input
                  type="date"
                  className="mt-1"
                  value={task.start_date || ''}
                  onChange={(e) => updateMutation.mutate({ start_date: e.target.value || null } as any)}
                />
              </div>

              <div>
                <Label className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> Срок
                </Label>
                <Input
                  type="date"
                  className="mt-1"
                  value={task.due_date || ''}
                  onChange={(e) => updateMutation.mutate({ due_date: e.target.value || null } as any)}
                />
              </div>

              <Separator />

              {/* Timestamps */}
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Создана: {new Date(task.created_at).toLocaleString('ru')}
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Обновлена: {new Date(task.updated_at).toLocaleString('ru')}
                </div>
                {task.completed_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Завершена: {new Date(task.completed_at).toLocaleString('ru')}
                  </div>
                )}
              </div>

            </CardContent>
          </Card>
        </div>
      </div>
    </TasksLayout>
  );
};

export default HRTaskDetail;
