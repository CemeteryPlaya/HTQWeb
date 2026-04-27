import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { PhoneInput } from '@/components/ui/phone-input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Check, ChevronsUpDown, UserPlus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useHRLevel } from '@/hooks/useHRLevel';

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
  // Sensitive (Senior-only — absent from API response for Junior)
  salary?: string | null;
  bonus?: string | null;
  passport_data?: string;
  bank_account?: string;
  // SRO (read-only for Junior)
  sro_permit_number?: string;
  sro_permit_expiry?: string | null;
  safety_cert_number?: string;
  safety_cert_expiry?: string | null;
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
  const { isSenior, isLoading: levelLoading } = useHRLevel();
  const { data: employees, isLoading, error } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: async () => {
      const res = await api.get<Employee[]>('hr/v1/employees/');
      return res.data;
    },
  });

  const { data: departments } = useQuery({
    queryKey: ['hr-departments'],
    queryFn: async () => {
      const res = await api.get<Department[]>('hr/v1/departments/');
      return res.data;
    },
  });

  const { data: positions } = useQuery({
    queryKey: ['hr-positions'],
    queryFn: async () => {
      const res = await api.get<Position[]>('hr/v1/positions/');
      return res.data;
    },
  });

  const { data: users } = useQuery({
    queryKey: ['hr-employee-users'],
    queryFn: async () => {
      const res = await api.get<HRUser[]>('hr/v1/employees/users/');
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
    // Senior-only fields
    salary: '',
    bonus: '',
    passport_data: '',
    bank_account: '',
    // SRO fields
    sro_permit_number: '',
    sro_permit_expiry: '',
    safety_cert_number: '',
    safety_cert_expiry: '',
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
      // Senior-only fields — only send when user is Senior
      if (isSenior) {
        payload.salary = form.salary ? Number(form.salary) : null;
        payload.bonus = form.bonus ? Number(form.bonus) : null;
        payload.passport_data = form.passport_data || '';
        payload.bank_account = form.bank_account || '';
        payload.sro_permit_number = form.sro_permit_number || '';
        payload.sro_permit_expiry = form.sro_permit_expiry || null;
        payload.safety_cert_number = form.safety_cert_number || '';
        payload.safety_cert_expiry = form.safety_cert_expiry || null;
      }
      if (editing) {
        if (!payload.user) {
          delete payload.user;
        }
        const res = await api.put(`hr/v1/employees/${editing.id}/`, payload);
        return res.data;
      }
      const res = await api.post('hr/v1/employees/', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-employees'] });
      queryClient.invalidateQueries({ queryKey: ['hr-employee-users'] });
      setDialogOpen(false);
      setEditing(null);
      setForm({
        user: 'none', position: 'none', department: 'none', phone: '',
        date_hired: '', date_dismissed: '', status: 'active', notes: '',
        salary: '', bonus: '', passport_data: '', bank_account: '',
        sro_permit_number: '', sro_permit_expiry: '', safety_cert_number: '', safety_cert_expiry: '',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`hr/v1/employees/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-employees'] });
      queryClient.invalidateQueries({ queryKey: ['hr-employee-users'] });
    },
  });

  const [userPopoverOpen, setUserPopoverOpen] = useState(false);
  const [createUserOpen, setCreateUserOpen] = useState(false);
  const [newUserForm, setNewUserForm] = useState({ first_name: '', last_name: '', patronymic: '', email: '' });

  const createUserMutation = useMutation({
    mutationFn: async (data: typeof newUserForm) => {
      const res = await api.post<HRUser>('hr/v1/employees/users/', data);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['hr-employee-users'] });
      setForm((prev) => ({ ...prev, user: String(data.id) }));
      setCreateUserOpen(false);
      setNewUserForm({ first_name: '', last_name: '', patronymic: '', email: '' });
      setUserPopoverOpen(false);
    },
  });

  const startCreate = () => {
    setEditing(null);
    setForm({
      user: 'none', position: 'none', department: 'none', phone: '',
      date_hired: '', date_dismissed: '', status: 'active', notes: '',
      salary: '', bonus: '', passport_data: '', bank_account: '',
      sro_permit_number: '', sro_permit_expiry: '', safety_cert_number: '', safety_cert_expiry: '',
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
      salary: emp.salary ? String(emp.salary) : '',
      bonus: emp.bonus ? String(emp.bonus) : '',
      passport_data: emp.passport_data || '',
      bank_account: emp.bank_account || '',
      sro_permit_number: emp.sro_permit_number || '',
      sro_permit_expiry: emp.sro_permit_expiry || '',
      safety_cert_number: emp.safety_cert_number || '',
      safety_cert_expiry: emp.safety_cert_expiry || '',
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
    <>
      <HRLayout title={t('hr.pages.employees.title')} subtitle={t('hr.pages.employees.subtitle')}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="text-sm text-muted-foreground">{t('hr.common.total')}: {employees?.length || 0}</div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={startCreate} className="w-full sm:w-auto">{t('hr.pages.employees.add')}</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
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
                      <Popover open={userPopoverOpen} onOpenChange={setUserPopoverOpen}>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            role="combobox"
                            aria-expanded={userPopoverOpen}
                            className="w-full justify-between font-normal"
                          >
                            {form.user && form.user !== 'none'
                              ? users?.find((u) => String(u.id) === form.user)?.full_name || t('hr.pages.employees.placeholders.selectUser')
                              : t('hr.pages.employees.placeholders.selectUser')}
                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-[400px] p-0" align="start">
                          <Command>
                            <CommandInput placeholder={t('hr.pages.employees.searchUser')} />
                            <CommandEmpty>{t('hr.pages.employees.noUserFound')}</CommandEmpty>
                            <CommandList>
                              <CommandGroup>
                                <CommandItem
                                  value="none"
                                  onSelect={() => {
                                    setForm({ ...form, user: 'none' });
                                    setUserPopoverOpen(false);
                                  }}
                                >
                                  <Check className={cn("mr-2 h-4 w-4", form.user === 'none' ? "opacity-100" : "opacity-0")} />
                                  {t('hr.pages.employees.placeholders.selectUser')}
                                </CommandItem>
                                {users?.map((u) => (
                                  <CommandItem
                                    key={u.id}
                                    value={`${u.full_name} ${u.email}`}
                                    onSelect={() => {
                                      setForm({ ...form, user: String(u.id) });
                                      setUserPopoverOpen(false);
                                    }}
                                  >
                                    <Check className={cn("mr-2 h-4 w-4", form.user === String(u.id) ? "opacity-100" : "opacity-0")} />
                                    {u.full_name} ({u.email})
                                  </CommandItem>
                                ))}
                              </CommandGroup>
                              <CommandGroup>
                                <CommandItem
                                  onSelect={() => {
                                    setUserPopoverOpen(false);
                                    setCreateUserOpen(true);
                                  }}
                                  className="text-primary font-medium flex items-center gap-2 cursor-pointer"
                                >
                                  <UserPlus className="h-4 w-4" />
                                  {t('hr.pages.employees.createUser')}
                                </CommandItem>
                              </CommandGroup>
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>
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
                    <PhoneInput value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
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

                {/* ═══ СРО / Охрана труда (Senior — editable, Junior — read-only) ═══ */}
                <div className="border-t pt-4 mt-2">
                  <h4 className="text-sm font-semibold mb-3">{t('hr.pages.employees.sections.sro')}</h4>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="grid gap-2 text-sm">
                      {t('hr.pages.employees.fields.sroPermitNumber')}
                      <Input value={form.sro_permit_number} readOnly={!isSenior} onChange={(e) => setForm({ ...form, sro_permit_number: e.target.value })} />
                    </label>
                    <label className="grid gap-2 text-sm">
                      {t('hr.pages.employees.fields.sroPermitExpiry')}
                      <Input type="date" value={form.sro_permit_expiry} readOnly={!isSenior} onChange={(e) => setForm({ ...form, sro_permit_expiry: e.target.value })} />
                    </label>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2 mt-3">
                    <label className="grid gap-2 text-sm">
                      {t('hr.pages.employees.fields.safetyCertNumber')}
                      <Input value={form.safety_cert_number} readOnly={!isSenior} onChange={(e) => setForm({ ...form, safety_cert_number: e.target.value })} />
                    </label>
                    <label className="grid gap-2 text-sm">
                      {t('hr.pages.employees.fields.safetyCertExpiry')}
                      <Input type="date" value={form.safety_cert_expiry} readOnly={!isSenior} onChange={(e) => setForm({ ...form, safety_cert_expiry: e.target.value })} />
                    </label>
                  </div>
                </div>

                {/* ═══ Финансовые данные (только Senior HR) ═══ */}
                {isSenior && (
                  <div className="border-t pt-4 mt-2">
                    <h4 className="text-sm font-semibold mb-3">{t('hr.pages.employees.sections.financial')}</h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="grid gap-2 text-sm">
                        {t('hr.pages.employees.fields.salary')}
                        <Input type="number" value={form.salary} onChange={(e) => setForm({ ...form, salary: e.target.value })} />
                      </label>
                      <label className="grid gap-2 text-sm">
                        {t('hr.pages.employees.fields.bonus')}
                        <Input type="number" value={form.bonus} onChange={(e) => setForm({ ...form, bonus: e.target.value })} />
                      </label>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2 mt-3">
                      <label className="grid gap-2 text-sm">
                        {t('hr.pages.employees.fields.passportData')}
                        <Input value={form.passport_data} onChange={(e) => setForm({ ...form, passport_data: e.target.value })} />
                      </label>
                      <label className="grid gap-2 text-sm">
                        {t('hr.pages.employees.fields.bankAccount')}
                        <Input value={form.bank_account} onChange={(e) => setForm({ ...form, bank_account: e.target.value })} />
                      </label>
                    </div>
                  </div>
                )}

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

        <div className="bg-card rounded-2xl border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('hr.pages.employees.table.lastName', 'Фамилия')}</TableHead>
                <TableHead>{t('hr.pages.employees.table.firstName', 'Имя')}</TableHead>
                <TableHead>{t('hr.pages.employees.table.patronymic', 'Отчество')}</TableHead>
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
              {employees?.map((emp) => {
                const nameParts = emp.full_name ? emp.full_name.trim().split(/\s+/) : [];
                const lastName = nameParts[0] || '—';
                const firstName = nameParts[1] || '—';
                const patronymic = nameParts.slice(2).join(' ') || '—';

                return (
                  <TableRow key={emp.id}>
                    <TableCell className="font-medium">{lastName}</TableCell>
                    <TableCell>{firstName}</TableCell>
                    <TableCell>{patronymic}</TableCell>
                    <TableCell>{emp.email}</TableCell>
                    <TableCell>{emp.position_title || '—'}</TableCell>
                    <TableCell>{emp.department_name || '—'}</TableCell>
                    <TableCell>{emp.phone || '—'}</TableCell>
                    <TableCell>{statusLabels[emp.status] || emp.status}</TableCell>
                    <TableCell>{emp.date_hired ? new Date(emp.date_hired).toLocaleDateString() : '—'}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex flex-col items-end gap-2">
                        <Button size="sm" variant="outline" className="w-full" onClick={() => startEdit(emp)}>{t('hr.common.edit')}</Button>
                        {isSenior && (
                          <Button
                            size="sm"
                            variant="destructive"
                            className="w-full"
                            onClick={() => {
                              if (confirm(t('hr.pages.employees.deleteConfirm'))) {
                                deleteMutation.mutate(emp.id);
                              }
                            }}
                          >
                            {t('hr.common.delete')}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </HRLayout>

      {/* Create User Dialog */}
      <Dialog open={createUserOpen} onOpenChange={setCreateUserOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto z-[60]">
          <DialogHeader>
            <DialogTitle>{t('hr.pages.employees.createUserTitle')}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4">
            <label className="grid gap-2 text-sm">
              {t('hr.pages.employees.fields.lastName')}
              <Input
                value={newUserForm.last_name}
                onChange={(e) => setNewUserForm({ ...newUserForm, last_name: e.target.value })}
              />
            </label>
            <label className="grid gap-2 text-sm">
              {t('hr.pages.employees.fields.firstName')}
              <Input
                value={newUserForm.first_name}
                onChange={(e) => setNewUserForm({ ...newUserForm, first_name: e.target.value })}
              />
            </label>
            <label className="grid gap-2 text-sm">
              {t('hr.pages.employees.fields.patronymic')}
              <Input
                value={newUserForm.patronymic}
                onChange={(e) => setNewUserForm({ ...newUserForm, patronymic: e.target.value })}
              />
            </label>
            <label className="grid gap-2 text-sm">
              {t('hr.pages.employees.fields.email')}
              <Input
                type="email"
                value={newUserForm.email}
                onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })}
              />
            </label>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setCreateUserOpen(false)}>
                {t('hr.common.cancel')}
              </Button>
              <Button
                onClick={() => createUserMutation.mutate(newUserForm)}
                disabled={!newUserForm.last_name || !newUserForm.first_name || !newUserForm.email || createUserMutation.isPending}
              >
                {createUserMutation.isPending ? t('hr.common.saving') : t('hr.common.save')}
              </Button>
            </div>
            {createUserMutation.isError && (
              <p className="text-red-500 text-sm mt-2">
                {(createUserMutation.error as any)?.response?.data?.detail || t('hr.common.unknownError')}
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default HREmployees;
