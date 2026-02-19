import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useHRLevel } from '@/hooks/useHRLevel';

interface Position {
  id: number;
  title: string;
  department: number | null;
  department_name: string;
}

interface Department {
  id: number;
  name: string;
}

const HRPositions = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { isSenior } = useHRLevel();
  const { data: positions, isLoading, error } = useQuery({
    queryKey: ['hr-positions'],
    queryFn: async () => {
      const res = await api.get<Position[]>('hr/positions/');
      return res.data;
    },
  });

  const { data: departments } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: async () => {
      const res = await api.get<Department[]>('hr/departments/');
      return res.data;
    },
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Position | null>(null);
  const [form, setForm] = useState({ title: '', department: '' });
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [sortKey, setSortKey] = useState<'title' | 'department'>('title');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        title: form.title,
        department: Number(form.department),
      };
      if (editing) {
        const res = await api.put(`hr/positions/${editing.id}/`, payload);
        return res.data;
      }
      const res = await api.post('hr/positions/', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-positions'] });
      setDialogOpen(false);
      setEditing(null);
      setForm({ title: '', department: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`hr/positions/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-positions'] }),
  });

  const startCreate = () => {
    setEditing(null);
    setForm({ title: '', department: '' });
    setDialogOpen(true);
  };

  const startEdit = (pos: Position) => {
    setEditing(pos);
    setForm({ title: pos.title || '', department: pos.department ? String(pos.department) : '' });
    setDialogOpen(true);
  };

  const filteredPositions = (positions ?? []).filter((pos) => {
    if (departmentFilter === 'all') return true;
    return String(pos.department ?? '') === departmentFilter;
  }).sort((a, b) => {
    if (sortKey === 'department') {
      const left = a.department_name?.toLowerCase() ?? '';
      const right = b.department_name?.toLowerCase() ?? '';
      return sortDir === 'asc' ? left.localeCompare(right) : right.localeCompare(left);
    }
    const left = a.title?.toLowerCase() ?? '';
    const right = b.title?.toLowerCase() ?? '';
    return sortDir === 'asc' ? left.localeCompare(right) : right.localeCompare(left);
  });
  const selectedDepartmentName = departments?.find((dept) => String(dept.id) === departmentFilter)?.name;

  const toggleSort = (key: 'title' | 'department') => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir('asc');
      return;
    }
    setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  };

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
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {t('hr.common.total')}: {filteredPositions.length}{positions && departmentFilter !== 'all' ? ` / ${positions.length}` : ''}
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={startCreate}>{t('hr.pages.positions.create')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editing ? t('hr.pages.positions.edit') : t('hr.pages.positions.new')}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <label className="grid gap-2 text-sm">
                {t('hr.pages.positions.fields.title')}
                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              </label>
              <label className="grid gap-2 text-sm">
                {t('hr.pages.positions.fields.department')}
                <Select value={form.department} onValueChange={(value) => setForm({ ...form, department: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('hr.pages.positions.placeholders.selectDepartment')} />
                  </SelectTrigger>
                  <SelectContent>
                    {departments?.map((dept) => (
                      <SelectItem key={dept.id} value={String(dept.id)}>
                        {dept.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>{t('hr.common.cancel')}</Button>
                <Button onClick={() => saveMutation.mutate()} disabled={!form.title || !form.department || saveMutation.isPending}>
                  {saveMutation.isPending ? t('hr.common.saving') : t('hr.common.save')}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-card rounded-2xl border mt-6">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <button
                  type="button"
                  onClick={() => toggleSort('title')}
                  className="inline-flex items-center gap-2 hover:underline"
                >
                  {t('hr.pages.positions.table.positionTitle')}
                  {sortKey === 'title' && (
                    <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>
                  )}
                </button>
              </TableHead>
              <TableHead>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleSort('department')}
                    className="inline-flex items-center gap-2 hover:underline"
                  >
                    {t('hr.pages.positions.table.department')}
                    {sortKey === 'department' && (
                      <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>
                    )}
                  </button>
                  {departmentFilter !== 'all' && selectedDepartmentName && (
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:underline"
                      onClick={() => setDepartmentFilter('all')}
                      aria-label="Clear department filter"
                    >
                      {selectedDepartmentName} ×
                    </button>
                  )}
                </div>
              </TableHead>
              <TableHead className="text-right">{t('hr.pages.positions.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredPositions.map((pos) => (
              <TableRow key={pos.id}>
                <TableCell className="font-medium">{pos.title}</TableCell>
                <TableCell>
                  {pos.department_name ? (
                    <button
                      type="button"
                      className="text-left hover:underline"
                      onClick={() => {
                        const next = String(pos.department ?? '');
                        setDepartmentFilter((prev) => (prev === next ? 'all' : next));
                      }}
                    >
                      {pos.department_name}
                    </button>
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="outline" onClick={() => startEdit(pos)}>{t('hr.common.edit')}</Button>
                    {isSenior && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm(t('hr.pages.positions.deleteConfirm')))
                        {
                          deleteMutation.mutate(pos.id);
                        }
                      }}
                    >
                      {t('hr.common.delete')}
                    </Button>
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
