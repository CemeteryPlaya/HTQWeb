import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useHRLevel } from '@/hooks/useHRLevel';

interface LevelThreshold {
  id: number;
  level_number: number;
  weight_from: number;
  weight_to: number;
  label: string | null;
}

interface Position {
  id: number;
  title: string;
  department_id: number | null;
  department_name?: string;
  weight: number;
  level: number;
  grade: number;
}

interface Department {
  id: number;
  name: string;
}

const LEVEL_COLORS: Record<number, string> = {
  1: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  2: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  3: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  4: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  5: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
};

function getLevelColor(level: number): string {
  return LEVEL_COLORS[level] ?? LEVEL_COLORS[5];
}

function WeightCell({
  position,
  canEdit,
  onSave,
}: {
  position: Position;
  canEdit: boolean;
  onSave: (id: number, weight: number) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(position.weight));
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const startEdit = () => {
    if (!canEdit) return;
    setDraft(String(position.weight));
    setEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const commit = async () => {
    const val = parseInt(draft, 10);
    if (isNaN(val) || val < 0 || val === position.weight) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(position.id, val);
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="number"
        min={0}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit();
          if (e.key === 'Escape') setEditing(false);
        }}
        className="w-20 rounded border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        disabled={saving}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={startEdit}
      title={canEdit ? 'Нажмите чтобы изменить вес' : undefined}
      className={`font-mono text-sm tabular-nums ${canEdit ? 'cursor-pointer hover:underline' : 'cursor-default'}`}
    >
      {position.weight}
    </button>
  );
}

const HRPositions = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { isSenior } = useHRLevel();

  const { data: positionsRaw, isLoading, error } = useQuery({
    queryKey: ['hr-positions-v1'],
    queryFn: async () => {
      const res = await api.get<{ items: Position[]; total: number } | Position[]>(
        'hr/v1/positions/?limit=200',
      );
      const data = res.data as any;
      return Array.isArray(data) ? data : (data.items ?? []);
    },
  });
  const positions: Position[] = positionsRaw ?? [];

  const { data: departments } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: async () => {
      const res = await api.get<Department[]>('hr/v1/departments/');
      return res.data;
    },
  });

  const { data: thresholds } = useQuery({
    queryKey: ['hr-level-thresholds'],
    queryFn: async () => {
      const res = await api.get<LevelThreshold[]>('hr/v1/positions/levels/');
      return res.data;
    },
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPos, setEditingPos] = useState<Position | null>(null);
  const [form, setForm] = useState({ title: '', department_id: '', weight: '100', grade: '1' });
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [sortKey, setSortKey] = useState<'weight' | 'title' | 'department'>('weight');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        title: form.title,
        department_id: Number(form.department_id),
        weight: Number(form.weight),
        grade: Number(form.grade),
      };
      if (editingPos) {
        return api.put(`hr/v1/positions/${editingPos.id}/`, payload);
      }
      return api.post('hr/v1/positions/', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-positions-v1'] });
      setDialogOpen(false);
      setEditingPos(null);
      setForm({ title: '', department_id: '', weight: '100', grade: '1' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`hr/v1/positions/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-positions-v1'] }),
  });

  const updateWeight = async (id: number, weight: number) => {
    await api.patch(`hr/v1/positions/${id}/weight`, { weight });
    queryClient.invalidateQueries({ queryKey: ['hr-positions-v1'] });
  };

  const startCreate = () => {
    setEditingPos(null);
    setForm({ title: '', department_id: '', weight: '100', grade: '1' });
    setDialogOpen(true);
  };

  const startEdit = (pos: Position) => {
    setEditingPos(pos);
    setForm({
      title: pos.title,
      department_id: pos.department_id ? String(pos.department_id) : '',
      weight: String(pos.weight),
      grade: String(pos.grade),
    });
    setDialogOpen(true);
  };

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey !== key) { setSortKey(key); setSortDir('asc'); return; }
    setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  };

  const filtered = positions
    .filter((p) => departmentFilter === 'all' || String(p.department_id) === departmentFilter)
    .sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      if (sortKey === 'weight') return (a.weight - b.weight) * dir;
      if (sortKey === 'title') return a.title.localeCompare(b.title) * dir;
      return (a.department_name ?? '').localeCompare(b.department_name ?? '') * dir;
    });

  if (isLoading) {
    return (
      <HRLayout title={t('hr.pages.positions.title')} subtitle={t('hr.pages.positions.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center">{t('hr.common.loading')}</div>
      </HRLayout>
    );
  }
  if (error) {
    return (
      <HRLayout title={t('hr.pages.positions.title')} subtitle={t('hr.pages.positions.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center text-red-500">
          {t('hr.pages.positions.error')}
        </div>
      </HRLayout>
    );
  }

  return (
    <HRLayout title={t('hr.pages.positions.title')} subtitle={t('hr.pages.positions.subtitle')}>
      {/* Level legend */}
      {thresholds && thresholds.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {thresholds.map((th) => (
            <span key={th.id} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${getLevelColor(th.level_number)}`}>
              L{th.level_number}{th.label ? `: ${th.label}` : ''} ({th.weight_from}–{th.weight_to})
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="text-sm text-muted-foreground">
            {t('hr.common.total')}: {filtered.length}
            {positions.length !== filtered.length ? ` / ${positions.length}` : ''}
          </div>
          <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
            <SelectTrigger className="h-8 w-40 text-xs">
              <SelectValue placeholder="Все отделы" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все отделы</SelectItem>
              {departments?.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isSenior && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={startCreate}>{t('hr.pages.positions.create')}</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>
                  {editingPos ? t('hr.pages.positions.edit') : t('hr.pages.positions.new')}
                </DialogTitle>
              </DialogHeader>
              <div className="grid gap-4">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.positions.fields.title')}
                  <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </label>
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.positions.fields.department')}
                  <Select value={form.department_id} onValueChange={(v) => setForm({ ...form, department_id: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('hr.pages.positions.placeholders.selectDepartment')} />
                    </SelectTrigger>
                    <SelectContent>
                      {departments?.map((d) => (
                        <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <label className="grid gap-2 text-sm">
                    Вес (weight)
                    <Input
                      type="number"
                      min={0}
                      value={form.weight}
                      onChange={(e) => setForm({ ...form, weight: e.target.value })}
                    />
                    <span className="text-xs text-muted-foreground">Меньше = выше в иерархии</span>
                  </label>
                  <label className="grid gap-2 text-sm">
                    Грейд (1–10)
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={form.grade}
                      onChange={(e) => setForm({ ...form, grade: e.target.value })}
                    />
                  </label>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setDialogOpen(false)}>
                    {t('hr.common.cancel')}
                  </Button>
                  <Button
                    onClick={() => saveMutation.mutate()}
                    disabled={!form.title || !form.department_id || saveMutation.isPending}
                  >
                    {saveMutation.isPending ? t('hr.common.saving') : t('hr.common.save')}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="bg-card rounded-2xl border mt-4 overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20">
                <button type="button" onClick={() => toggleSort('weight')} className="inline-flex items-center gap-1 hover:underline">
                  Вес {sortKey === 'weight' && <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>}
                </button>
              </TableHead>
              <TableHead className="w-16">Уровень</TableHead>
              <TableHead>
                <button type="button" onClick={() => toggleSort('title')} className="inline-flex items-center gap-1 hover:underline">
                  {t('hr.pages.positions.table.positionTitle')}
                  {sortKey === 'title' && <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>}
                </button>
              </TableHead>
              <TableHead>
                <button type="button" onClick={() => toggleSort('department')} className="inline-flex items-center gap-1 hover:underline">
                  {t('hr.pages.positions.table.department')}
                  {sortKey === 'department' && <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>}
                </button>
              </TableHead>
              <TableHead className="text-right">{t('hr.pages.positions.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((pos) => (
              <TableRow key={pos.id}>
                <TableCell>
                  <WeightCell position={pos} canEdit={isSenior} onSave={updateWeight} />
                </TableCell>
                <TableCell>
                  <Badge className={`text-xs ${getLevelColor(pos.level)}`} variant="outline">
                    L{pos.level}
                  </Badge>
                </TableCell>
                <TableCell className="font-medium">{pos.title}</TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {pos.department_name ?? '—'}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    {isSenior && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => startEdit(pos)}>
                          {t('hr.common.edit')}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            if (confirm(t('hr.pages.positions.deleteConfirm'))) {
                              deleteMutation.mutate(pos.id);
                            }
                          }}
                        >
                          {t('hr.common.delete')}
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </HRLayout>
  );
};

export default HRPositions;
