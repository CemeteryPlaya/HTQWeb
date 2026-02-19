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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Employee {
  id: number;
  user: number;
  position?: number | null;
  department?: number | null;
  full_name: string;
  username: string;
  email: string;
  position_title: string;
  department_name: string;
  phone: string;
  date_hired: string;
  date_dismissed?: string | null;
  status: string;
  notes?: string;
}

interface Department {
  id: number;
  name: string;
}

interface Position {
  id: number;
  title: string;
}

interface HRUser {
  id: number;
  full_name: string;
  email: string;
}

const HREmployees = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: employees, isLoading, error } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: async () => {
      const res = await api.get<Employee[]>('hr/employees/');
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

  const { data: positions } = useQuery({
    queryKey: ['hr-positions'],
    queryFn: async () => {
      const res = await api.get<Position[]>('hr/positions/');
      return res.data;
    },
  });

  const { data: users } = useQuery({
    queryKey: ['hr-employee-users'],
    queryFn: async () => {
      const res = await api.get<HRUser[]>('hr/employees/users/');
      return res.data;
    },
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [form, setForm] = useState({
    user: 'none',
    position: 'none',
    department: 'none',
    phone: '',
    date_hired: '',
    date_dismissed: '',
    status: 'active',
    notes: '',
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload: any = {
        user: form.user === 'none' ? undefined : Number(form.user),
        position: form.position === 'none' ? null : Number(form.position),
        department: form.department === 'none' ? null : Number(form.department),
        phone: form.phone || '',
        date_hired: form.date_hired || null,
        date_dismissed: form.date_dismissed || null,
        status: form.status,
        notes: form.notes || '',
      };
      if (editing) {
        if (!payload.user) {
          delete payload.user;
        }
        const res = await api.put(`hr/employees/${editing.id}/`, payload);
        return res.data;
      }
      const res = await api.post('hr/employees/', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-employees'] });
      queryClient.invalidateQueries({ queryKey: ['hr-employee-users'] });
      setDialogOpen(false);
      setEditing(null);
      setForm({
        user: 'none',
        position: 'none',
        department: 'none',
        phone: '',
        date_hired: '',
        date_dismissed: '',
        status: 'active',
        notes: '',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`hr/employees/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-employees'] });
      queryClient.invalidateQueries({ queryKey: ['hr-employee-users'] });
    },
  });

  const startCreate = () => {
    setEditing(null);
    setForm({
      user: 'none',
      position: 'none',
      department: 'none',
      phone: '',
      date_hired: '',
      date_dismissed: '',
      status: 'active',
      notes: '',
    });
    setDialogOpen(true);
  };

  const startEdit = (emp: Employee) => {
    setEditing(emp);
    setForm({
      user: emp.user ? String(emp.user) : 'none',
      position: emp.position ? String(emp.position) : 'none',
      department: emp.department ? String(emp.department) : 'none',
      phone: emp.phone || '',
      date_hired: emp.date_hired || '',
      date_dismissed: emp.date_dismissed || '',
      status: emp.status || 'active',
      notes: emp.notes || '',
    });
    setDialogOpen(true);
  };

  const statusLabels: Record<string, string> = {
    active: t('hr.pages.employees.status.active'),
    on_leave: t('hr.pages.employees.status.onLeave'),
    dismissed: t('hr.pages.employees.status.dismissed'),
  };

  if (isLoading) {
    return (
      <HRLayout title={t('hr.pages.employees.title')} subtitle={t('hr.pages.employees.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center">{t('hr.common.loading')}</div>
      </HRLayout>
    );
  }

  if (error) {
    return (
      <HRLayout title={t('hr.pages.employees.title')} subtitle={t('hr.pages.employees.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center text-red-500">
          <h2 className="text-xl font-semibold mb-2">{t('hr.pages.employees.error')}</h2>
          <p>{(error as any)?.message || t('hr.common.unknownError')}</p>
        </div>
      </HRLayout>
    );
  }

  return (
    <HRLayout title={t('hr.pages.employees.title')} subtitle={t('hr.pages.employees.subtitle')}>
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">{t('hr.common.total')}: {employees?.length || 0}</div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={startCreate}>{t('hr.pages.employees.add')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editing ? t('hr.pages.employees.edit') : t('hr.pages.employees.new')}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                {editing ? (
                  <label className="grid gap-2 text-sm">
                    {t('hr.pages.employees.fields.user')}
                    <Input value={`${editing.full_name} (${editing.email})`} readOnly />
                  </label>
                ) : (
                  <label className="grid gap-2 text-sm">
                    {t('hr.pages.employees.fields.user')}
                    <Select value={form.user} onValueChange={(value) => setForm({ ...form, user: value })}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('hr.pages.employees.placeholders.selectUser')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">{t('hr.pages.employees.placeholders.selectUser')}</SelectItem>
                        {users?.map((user) => (
                          <SelectItem key={user.id} value={String(user.id)}>
                            {user.full_name} ({user.email})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </label>
                )}
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.employees.fields.status')}
                  <Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('hr.pages.employees.placeholders.selectStatus')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">{t('hr.pages.employees.status.active')}</SelectItem>
                      <SelectItem value="on_leave">{t('hr.pages.employees.status.onLeave')}</SelectItem>
                      <SelectItem value="dismissed">{t('hr.pages.employees.status.dismissed')}</SelectItem>
                    </SelectContent>
                  </Select>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.employees.fields.position')}
                  <Select value={form.position} onValueChange={(value) => setForm({ ...form, position: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('hr.pages.employees.placeholders.selectPosition')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{t('hr.common.noPosition')}</SelectItem>
                      {positions?.map((pos) => (
                        <SelectItem key={pos.id} value={String(pos.id)}>
                          {pos.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.employees.fields.department')}
                  <Select value={form.department} onValueChange={(value) => setForm({ ...form, department: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('hr.pages.employees.placeholders.selectDepartment')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{t('hr.common.noDepartment')}</SelectItem>
                      {departments?.map((dept) => (
                        <SelectItem key={dept.id} value={String(dept.id)}>
                          {dept.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.employees.fields.phone')}
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </label>
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.employees.fields.dateHired')}
                  <Input type="date" value={form.date_hired} onChange={(e) => setForm({ ...form, date_hired: e.target.value })} />
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.employees.fields.dateDismissed')}
                  <Input type="date" value={form.date_dismissed} onChange={(e) => setForm({ ...form, date_dismissed: e.target.value })} />
                </label>
              </div>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.employees.fields.notes')}
                <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </label>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>{t('hr.common.cancel')}</Button>
                <Button onClick={() => saveMutation.mutate()} disabled={(!editing && form.user === 'none') || saveMutation.isPending}>
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
              <TableHead>{t('hr.pages.employees.table.name')}</TableHead>
              <TableHead>{t('hr.pages.employees.table.email')}</TableHead>
              <TableHead>{t('hr.pages.employees.table.position')}</TableHead>
              <TableHead>{t('hr.pages.employees.table.department')}</TableHead>
              <TableHead>{t('hr.pages.employees.table.phone')}</TableHead>
              <TableHead>{t('hr.pages.employees.table.status')}</TableHead>
              <TableHead>{t('hr.pages.employees.table.hired')}</TableHead>
              <TableHead className="text-right">{t('hr.pages.employees.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {employees?.map((emp) => (
              <TableRow key={emp.id}>
                <TableCell className="font-medium">{emp.full_name}</TableCell>
                <TableCell>{emp.email}</TableCell>
                <TableCell>{emp.position_title || '—'}</TableCell>
                <TableCell>{emp.department_name || '—'}</TableCell>
                <TableCell>{emp.phone || '—'}</TableCell>
                <TableCell>{statusLabels[emp.status] || emp.status}</TableCell>
                <TableCell>{emp.date_hired ? new Date(emp.date_hired).toLocaleDateString() : '—'}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="outline" onClick={() => startEdit(emp)}>{t('hr.common.edit')}</Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm(t('hr.pages.employees.deleteConfirm')))
                        {
                          deleteMutation.mutate(emp.id);
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

export default HREmployees;
