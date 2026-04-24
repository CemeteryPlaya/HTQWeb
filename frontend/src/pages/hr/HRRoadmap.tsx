import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { TasksLayout } from '@/components/tasks/TasksLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { toast } from 'sonner';
import {
  Plus, ChevronDown, ChevronRight, Calendar, Target,
  AlertCircle, CheckSquare, Bug, BookOpen, Layers, ListTodo,
} from 'lucide-react';
import {
  fetchVersions, createVersion, updateVersion, deleteVersion,
  fetchVersionTasks,
} from '@/api/tasks';
import api from '@/api/client';
import type { UserProfile } from '@/types/userProfile';
import type { ProjectVersion, VersionStatus, Task, TaskStatus, TaskType } from '@/types/tasks';

/* ---- Config ---- */

const VERSION_STATUS: Record<VersionStatus, { label: string; color: string }> = {
  planned: { label: 'Запланирована', color: 'bg-slate-500 text-white' },
  in_progress: { label: 'В работе', color: 'bg-blue-600 text-white' },
  released: { label: 'Выпущена', color: 'bg-green-500 text-white' },
  archived: { label: 'В архиве', color: 'bg-gray-400 text-white' },
};

const STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  open: { label: 'Открыта', color: 'bg-slate-500 text-white' },
  in_progress: { label: 'В работе', color: 'bg-blue-600 text-white' },
  in_review: { label: 'Ревью', color: 'bg-purple-500 text-white' },
  done: { label: 'Готова', color: 'bg-green-500 text-white' },
  closed: { label: 'Закрыта', color: 'bg-gray-600 text-white' },
};

const TYPE_ICONS: Record<TaskType, React.ReactNode> = {
  task: <CheckSquare className="h-4 w-4 text-blue-500" />,
  bug: <Bug className="h-4 w-4 text-red-500" />,
  story: <BookOpen className="h-4 w-4 text-green-500" />,
  epic: <Layers className="h-4 w-4 text-purple-500" />,
  subtask: <ListTodo className="h-4 w-4 text-gray-500" />,
};

/* ---- Timeline bar rendering helper ---- */

function TimelineBar({ version, minDate, totalDays }: {
  version: ProjectVersion; minDate: Date; totalDays: number;
}) {
  if (!version.start_date || !version.release_date || totalDays <= 0) return null;
  const start = new Date(version.start_date);
  const end = new Date(version.release_date);
  const leftPct = Math.max(0, (start.getTime() - minDate.getTime()) / (totalDays * 86400000) * 100);
  const widthPct = Math.max(2, (end.getTime() - start.getTime()) / (totalDays * 86400000) * 100);

  return (
    <div
      className="absolute h-8 rounded-md flex items-center px-2 text-xs font-medium text-white shadow-sm"
      style={{
        left: `${leftPct}%`,
        width: `${Math.min(widthPct, 100 - leftPct)}%`,
        backgroundColor: version.status === 'released' ? '#22c55e'
          : version.status === 'in_progress' ? '#3b82f6' : '#64748b',
      }}
      title={`${version.name}: ${version.start_date} → ${version.release_date}`}
    >
      <span className="truncate">{version.name}</span>
    </div>
  );
}

/* ---- Version Card with expandable tasks ---- */

function VersionCard({ version }: { version: ProjectVersion }) {
  const [open, setOpen] = useState(false);
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['hr-version-tasks', version.id],
    queryFn: () => fetchVersionTasks(version.id),
    enabled: open,
  });

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors">
            <div className="flex items-center gap-3">
              {open
                ? <ChevronDown className="h-5 w-5 text-muted-foreground" />
                : <ChevronRight className="h-5 w-5 text-muted-foreground" />}

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <CardTitle className="text-lg">{version.name}</CardTitle>
                  <Badge className={VERSION_STATUS[version.status]?.color}>
                    {VERSION_STATUS[version.status]?.label}
                  </Badge>
                </div>

                {version.description && (
                  <p className="text-sm text-muted-foreground line-clamp-1">{version.description}</p>
                )}

                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                  {version.start_date && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" /> Начало: {version.start_date}
                    </span>
                  )}
                  {version.release_date && (
                    <span className="flex items-center gap-1">
                      <Target className="h-3 w-3" /> Релиз: {version.release_date}
                    </span>
                  )}
                  <span>Задач: {version.task_count}</span>
                </div>
              </div>

              <div className="w-32 text-right">
                <div className="text-sm font-medium mb-1">{version.progress}%</div>
                <Progress value={version.progress} className="h-2" />
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="pt-0">
            {isLoading ? (
              <p className="text-muted-foreground text-sm py-4">Загрузка задач...</p>
            ) : !tasks || tasks.length === 0 ? (
              <p className="text-muted-foreground text-sm py-4">Нет задач для этой версии</p>
            ) : (
              <div className="space-y-1">
                {tasks.map((task: Task) => (
                  <Link
                    key={task.id}
                    to={`/tasks/${task.id}`}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted transition-colors"
                  >
                    {TYPE_ICONS[task.task_type]}
                    <span className="font-mono text-sm text-primary">{task.key}</span>
                    <span className="text-sm flex-1 truncate">{task.summary}</span>
                    <Badge className={STATUS_CONFIG[task.status]?.color} variant="secondary">
                      {STATUS_CONFIG[task.status]?.label}
                    </Badge>
                    {task.assignee_name && (
                      <span className="text-xs text-muted-foreground">{task.assignee_name}</span>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

/* ---- Main Roadmap Page ---- */

const HRRoadmap: React.FC = () => {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('list');
  const [form, setForm] = useState({
    name: '', description: '', status: 'planned' as VersionStatus,
    start_date: '', release_date: '',
  });

  const { data: versions = [], isLoading, error } = useQuery({
    queryKey: ['hr-versions'],
    queryFn: () => fetchVersions(),
  });

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const res = await api.get<UserProfile>('users/v1/profile/me');
      return res.data;
    }
  });

  const hasElevatedRoles = profile?.roles?.some((r: string) =>
    ['staff', 'admin', 'superuser', 'hr_manager', 'senior_hr', 'junior_hr', 'senior_manager', 'junior_manager'].includes(r)
  );
  const isRegularEmployee = !!(profile && !hasElevatedRoles);

  const createMutation = useMutation({
    mutationFn: (data: Partial<ProjectVersion>) => createVersion(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-versions'] });
      setCreateOpen(false);
      setForm({ name: '', description: '', status: 'planned', start_date: '', release_date: '' });
      toast.success('Версия создана');
    },
    onError: () => toast.error('Ошибка создания версии'),
  });

  /* Timeline calculations */
  const datedVersions = versions.filter((v) => v.start_date && v.release_date);
  let minDate = new Date();
  let maxDate = new Date();
  let totalDays = 0;
  if (datedVersions.length > 0) {
    const starts = datedVersions.map((v) => new Date(v.start_date!).getTime());
    const ends = datedVersions.map((v) => new Date(v.release_date!).getTime());
    minDate = new Date(Math.min(...starts));
    maxDate = new Date(Math.max(...ends));
    totalDays = Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / 86400000));
  }

  return (
    <TasksLayout title="Дорожная карта" subtitle="Версии, релизы и планирование">
      {/* Toolbar */}
      <Card>
        <CardContent className="p-4 flex flex-wrap items-center gap-3">
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              Список
            </Button>
            <Button
              variant={viewMode === 'timeline' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('timeline')}
            >
              Таймлайн
            </Button>
          </div>
          <div className="flex-1" />
          {!isRegularEmployee && (
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-1" /> Новая версия
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Content */}
      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Загрузка...</div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-500 py-8 justify-center">
          <AlertCircle className="h-5 w-5" /> Ошибка загрузки
        </div>
      ) : versions.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          Нет версий. Создайте первую версию для дорожной карты!
        </div>
      ) : viewMode === 'list' ? (
        /* ===== LIST VIEW ===== */
        <div className="space-y-3">
          {versions.map((v) => (
            <VersionCard key={v.id} version={v} />
          ))}
        </div>
      ) : (
        /* ===== TIMELINE VIEW ===== */
        <Card>
          <CardHeader><CardTitle>Таймлайн</CardTitle></CardHeader>
          <CardContent>
            {datedVersions.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                Для отображения таймлайна укажите даты начала и релиза у версий.
              </p>
            ) : (
              <div className="space-y-1">
                {/* Time axis labels */}
                <div className="flex justify-between text-xs text-muted-foreground mb-2 px-1">
                  <span>{minDate.toLocaleDateString('ru')}</span>
                  <span>{maxDate.toLocaleDateString('ru')}</span>
                </div>

                {/* Bars */}
                <div className="space-y-3">
                  {datedVersions.map((v) => (
                    <div key={v.id} className="flex items-center gap-3">
                      <div className="w-36 text-sm font-medium truncate">{v.name}</div>
                      <div className="flex-1 relative h-8 bg-muted rounded-md">
                        <TimelineBar version={v} minDate={minDate} totalDays={totalDays} />
                      </div>
                      <div className="w-12 text-right text-xs text-muted-foreground">
                        {v.progress}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Version Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Новая версия</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div>
              <Label>Название *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="v1.0.0"
              />
            </div>
            <div>
              <Label>Описание</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
              />
            </div>
            <div>
              <Label>Статус</Label>
              <Select
                value={form.status}
                onValueChange={(v) => setForm({ ...form, status: v as VersionStatus })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(VERSION_STATUS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Дата начала</Label>
                <Input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                />
              </div>
              <div>
                <Label>Дата релиза</Label>
                <Input
                  type="date"
                  value={form.release_date}
                  onChange={(e) => setForm({ ...form, release_date: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Отмена</Button>
            <Button
              disabled={!form.name.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate(form)}
            >
              {createMutation.isPending ? 'Создание...' : 'Создать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </TasksLayout>
  );
};

export default HRRoadmap;
