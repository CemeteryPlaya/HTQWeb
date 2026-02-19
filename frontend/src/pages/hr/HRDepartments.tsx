import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface Department {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

const HRDepartments = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: departments, isLoading, error } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: async () => {
      const res = await api.get<Department[]>('hr/departments/');
      return res.data;
    },
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [form, setForm] = useState({ name: '', description: '' });
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<'name' | 'created_at'>('created_at');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        const res = await api.put(`hr/departments/${editing.id}/`, form);
        return res.data;
      }
      const res = await api.post('hr/departments/', form);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-departments'] });
      setDialogOpen(false);
      setEditing(null);
      setForm({ name: '', description: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`hr/departments/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-departments'] }),
  });

  const startCreate = () => {
    setEditing(null);
    setForm({ name: '', description: '' });
    setDialogOpen(true);
  };

  const startEdit = (dept: Department) => {
    setEditing(dept);
    setForm({ name: dept.name || '', description: dept.description || '' });
    setDialogOpen(true);
  };

  const toggleSort = (key: 'name' | 'created_at') => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir(key === 'name' ? 'asc' : 'desc');
      return;
    }
    setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  };

  const filteredDepartments = (departments ?? [])
    .filter((dept) => dept.name?.toLowerCase().includes(search.trim().toLowerCase()))
    .sort((a, b) => {
      if (sortKey === 'name') {
        const left = a.name?.toLowerCase() ?? '';
        const right = b.name?.toLowerCase() ?? '';
        return sortDir === 'asc' ? left.localeCompare(right) : right.localeCompare(left);
      }
      const left = new Date(a.created_at).getTime();
      const right = new Date(b.created_at).getTime();
      return sortDir === 'asc' ? left - right : right - left;
    });

  if (isLoading) {
    return (
      <HRLayout title={t('hr.pages.departments.title')} subtitle={t('hr.pages.departments.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center">{t('hr.common.loading')}</div>
      </HRLayout>
    );
  }
  if (error) {
    return (
      <HRLayout title={t('hr.pages.departments.title')} subtitle={t('hr.pages.departments.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center text-red-500">
          {t('hr.pages.departments.error')}
        </div>
      </HRLayout>
    );
  }

  return (
    <HRLayout title={t('hr.pages.departments.title')} subtitle={t('hr.pages.departments.subtitle')}>
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">{t('hr.common.total')}: {filteredDepartments.length}</div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={startCreate}>{t('hr.pages.departments.create')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editing ? t('hr.pages.departments.edit') : t('hr.pages.departments.new')}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <label className="grid gap-2 text-sm">
                {t('hr.pages.departments.fields.name')}
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </label>
              <label className="grid gap-2 text-sm">
                {t('hr.pages.departments.fields.description')}
                <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </label>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>{t('hr.common.cancel')}</Button>
                <Button onClick={() => saveMutation.mutate()} disabled={!form.name || saveMutation.isPending}>
                  {saveMutation.isPending ? t('hr.common.saving') : t('hr.common.save')}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-6 flex items-center gap-3">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('hr.pages.departments.searchPlaceholder')}
          className="max-w-sm"
        />
      </div>

      <div className="bg-card rounded-2xl border mt-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <button
                  type="button"
                  onClick={() => toggleSort('name')}
                  className="inline-flex items-center gap-2 hover:underline"
                >
                  {t('hr.pages.departments.table.name')}
                  {sortKey === 'name' && (
                    <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>
                  )}
                </button>
              </TableHead>
              <TableHead>{t('hr.pages.departments.table.description')}</TableHead>
              <TableHead>
                <button
                  type="button"
                  onClick={() => toggleSort('created_at')}
                  className="inline-flex items-center gap-2 hover:underline"
                >
                  {t('hr.pages.departments.table.created')}
                  {sortKey === 'created_at' && (
                    <span className="text-xs text-muted-foreground">{sortDir.toUpperCase()}</span>
                  )}
                </button>
              </TableHead>
              <TableHead className="text-right">{t('hr.pages.departments.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredDepartments.map((dept) => (
              <TableRow key={dept.id}>
                <TableCell className="font-medium">{dept.name}</TableCell>
                <TableCell>{dept.description || '—'}</TableCell>
                <TableCell>{new Date(dept.created_at).toLocaleDateString()}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="outline" onClick={() => startEdit(dept)}>{t('hr.common.edit')}</Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm(t('hr.pages.departments.deleteConfirm')))
                        {
                          deleteMutation.mutate(dept.id);
                        }
                      }}
                    >
                      {t('hr.common.delete')}
                    </Button>
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

export default HRDepartments;
