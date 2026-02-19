import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Application {
  id: number;
  vacancy: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  vacancy_title: string;
  status: string;
  created_at: string;
  notes?: string;
  resume?: string | null;
  cover_letter?: string;
}

interface Vacancy {
  id: number;
  title: string;
}

const HRApplications = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: applications, isLoading, error } = useQuery({
    queryKey: ['hr-applications'],
    queryFn: async () => {
      const res = await api.get<Application[]>('hr/applications/');
      return res.data;
    },
  });

  const { data: vacancies } = useQuery({
    queryKey: ['hr-vacancies'],
    queryFn: async () => {
      const res = await api.get<Vacancy[]>('hr/vacancies/');
      return res.data;
    },
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Application | null>(null);
  const [form, setForm] = useState({
    vacancy: 'none',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    status: 'new',
    notes: '',
    cover_letter: '',
    resume: null as File | null,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      if (form.vacancy !== 'none') formData.append('vacancy', form.vacancy);
      formData.append('first_name', form.first_name);
      formData.append('last_name', form.last_name);
      formData.append('email', form.email);
      formData.append('phone', form.phone || '');
      formData.append('status', form.status);
      formData.append('notes', form.notes || '');
      formData.append('cover_letter', form.cover_letter || '');
      if (form.resume) formData.append('resume', form.resume);

      if (editing) {
        const res = await api.put(`hr/applications/${editing.id}/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        return res.data;
      }
      const res = await api.post('hr/applications/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-applications'] });
      setDialogOpen(false);
      setEditing(null);
      setForm({
        vacancy: 'none',
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        status: 'new',
        notes: '',
        cover_letter: '',
        resume: null,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`hr/applications/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-applications'] }),
  });

  const startCreate = () => {
    setEditing(null);
    setForm({
      vacancy: 'none',
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      status: 'new',
      notes: '',
      cover_letter: '',
      resume: null,
    });
    setDialogOpen(true);
  };

  const startEdit = (app: Application) => {
    setEditing(app);
    setForm({
      vacancy: app.vacancy ? String(app.vacancy) : 'none',
      first_name: app.first_name || '',
      last_name: app.last_name || '',
      email: app.email || '',
      phone: app.phone || '',
      status: app.status || 'new',
      notes: app.notes || '',
      cover_letter: app.cover_letter || '',
      resume: null,
    });
    setDialogOpen(true);
  };

  const statusLabels: Record<string, string> = {
    new: t('hr.pages.applications.status.new'),
    reviewed: t('hr.pages.applications.status.reviewed'),
    interview: t('hr.pages.applications.status.interview'),
    offered: t('hr.pages.applications.status.offered'),
    rejected: t('hr.pages.applications.status.rejected'),
    hired: t('hr.pages.applications.status.hired'),
  };

  if (isLoading) {
    return (
      <HRLayout title={t('hr.pages.applications.title')} subtitle={t('hr.pages.applications.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center">{t('hr.common.loading')}</div>
      </HRLayout>
    );
  }
  if (error) {
    return (
      <HRLayout title={t('hr.pages.applications.title')} subtitle={t('hr.pages.applications.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center text-red-500">
          {t('hr.pages.applications.error')}
        </div>
      </HRLayout>
    );
  }

  return (
    <HRLayout title={t('hr.pages.applications.title')} subtitle={t('hr.pages.applications.subtitle')}>
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">{t('hr.common.total')}: {applications?.length || 0}</div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={startCreate}>{t('hr.pages.applications.add')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editing ? t('hr.pages.applications.edit') : t('hr.pages.applications.new')}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <label className="grid gap-2 text-sm">
                {t('hr.pages.applications.fields.vacancy')}
                <Select value={form.vacancy} onValueChange={(value) => setForm({ ...form, vacancy: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('hr.pages.applications.placeholders.selectVacancy')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t('hr.pages.applications.placeholders.selectVacancy')}</SelectItem>
                    {vacancies?.map((vacancy) => (
                      <SelectItem key={vacancy.id} value={String(vacancy.id)}>
                        {vacancy.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.applications.fields.firstName')}
                  <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
                </label>
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.applications.fields.lastName')}
                  <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.applications.fields.email')}
                  <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </label>
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.applications.fields.phone')}
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </label>
              </div>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.applications.fields.status')}
                <Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('hr.pages.applications.placeholders.selectStatus')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="new">{t('hr.pages.applications.status.new')}</SelectItem>
                    <SelectItem value="reviewed">{t('hr.pages.applications.status.reviewed')}</SelectItem>
                    <SelectItem value="interview">{t('hr.pages.applications.status.interview')}</SelectItem>
                    <SelectItem value="offered">{t('hr.pages.applications.status.offered')}</SelectItem>
                    <SelectItem value="rejected">{t('hr.pages.applications.status.rejected')}</SelectItem>
                    <SelectItem value="hired">{t('hr.pages.applications.status.hired')}</SelectItem>
                  </SelectContent>
                </Select>
              </label>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.applications.fields.coverLetter')}
                <Textarea value={form.cover_letter} onChange={(e) => setForm({ ...form, cover_letter: e.target.value })} />
              </label>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.applications.fields.notes')}
                <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </label>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.applications.fields.resume')}
                <Input type="file" onChange={(e: any) => setForm({ ...form, resume: e.target.files?.[0] || null })} />
              </label>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>{t('hr.common.cancel')}</Button>
                <Button onClick={() => saveMutation.mutate()} disabled={form.vacancy === 'none' || !form.email || saveMutation.isPending}>
                  {saveMutation.isPending ? t('hr.common.saving') : t('hr.common.save')}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-card rounded-2xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('hr.pages.applications.table.applicant')}</TableHead>
              <TableHead>{t('hr.pages.applications.table.email')}</TableHead>
              <TableHead>{t('hr.pages.applications.table.phone')}</TableHead>
              <TableHead>{t('hr.pages.applications.table.vacancy')}</TableHead>
              <TableHead>{t('hr.pages.applications.table.status')}</TableHead>
              <TableHead>{t('hr.pages.applications.table.applied')}</TableHead>
              <TableHead className="text-right">{t('hr.pages.applications.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {applications?.map((app) => (
              <TableRow key={app.id}>
                <TableCell className="font-medium">{app.first_name} {app.last_name}</TableCell>
                <TableCell>{app.email}</TableCell>
                <TableCell>{app.phone || '—'}</TableCell>
                <TableCell>{app.vacancy_title}</TableCell>
                <TableCell>
                  <Badge>{statusLabels[app.status] || app.status}</Badge>
                </TableCell>
                <TableCell>{new Date(app.created_at).toLocaleDateString()}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="outline" onClick={() => startEdit(app)}>{t('hr.common.edit')}</Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm(t('hr.pages.applications.deleteConfirm')))
                        {
                          deleteMutation.mutate(app.id);
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

export default HRApplications;
