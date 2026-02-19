import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchAccounts, updateAccount, resetAccountPassword } from '@/api/hr';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Eye, EyeOff, RefreshCw, Copy, Check } from 'lucide-react';
import type { EmployeeAccount } from '@/types/hr';

const HRAccounts = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [editOpen, setEditOpen] = useState(false);
  const [editAccount, setEditAccount] = useState<EmployeeAccount | null>(null);
  const [form, setForm] = useState({ username: '', initial_password: '', is_active: true });
  const [visiblePasswords, setVisiblePasswords] = useState<Record<number, boolean>>({});
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const { data: accounts, isLoading, error } = useQuery({
    queryKey: ['hr-accounts', search],
    queryFn: () => fetchAccounts(search ? { search } : undefined),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<EmployeeAccount> }) =>
      updateAccount(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-accounts'] });
      setEditOpen(false);
    },
  });

  const resetMutation = useMutation({
    mutationFn: (id: number) => resetAccountPassword(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-accounts'] });
    },
  });

  const openEdit = (account: EmployeeAccount) => {
    setEditAccount(account);
    setForm({
      username: account.username,
      initial_password: account.initial_password,
      is_active: account.is_active,
    });
    setEditOpen(true);
  };

  const handleSave = () => {
    if (!editAccount) return;
    updateMutation.mutate({ id: editAccount.id, data: form });
  };

  const togglePasswordVisibility = (id: number) => {
    setVisiblePasswords((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyCredentials = async (account: EmployeeAccount) => {
    const text = `${t('hr.pages.accounts.fields.username')}: ${account.username}\n${t('hr.pages.accounts.fields.password')}: ${account.initial_password}`;
    await navigator.clipboard.writeText(text);
    setCopiedId(account.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (isLoading)
    return (
      <HRLayout title={t('hr.pages.accounts.title')} subtitle={t('hr.pages.accounts.subtitle')}>
        <div className="p-8">{t('hr.common.loading')}</div>
      </HRLayout>
    );

  if (error)
    return (
      <HRLayout title={t('hr.pages.accounts.title')} subtitle={t('hr.pages.accounts.subtitle')}>
        <div className="p-8 text-red-500">{t('hr.pages.accounts.error')}</div>
      </HRLayout>
    );

  return (
    <HRLayout title={t('hr.pages.accounts.title')} subtitle={t('hr.pages.accounts.subtitle')}>
      <div className="mb-4">
        <Input
          placeholder={t('hr.pages.accounts.searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
      </div>

      <div className="border rounded-lg overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('hr.pages.accounts.fields.employee')}</TableHead>
              <TableHead>{t('hr.pages.accounts.fields.email')}</TableHead>
              <TableHead>{t('hr.pages.accounts.fields.department')}</TableHead>
              <TableHead>{t('hr.pages.accounts.fields.position')}</TableHead>
              <TableHead>{t('hr.pages.accounts.fields.username')}</TableHead>
              <TableHead>{t('hr.pages.accounts.fields.password')}</TableHead>
              <TableHead>{t('hr.pages.accounts.fields.status')}</TableHead>
              <TableHead>{t('hr.common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(accounts || []).map((acc) => (
              <TableRow key={acc.id}>
                <TableCell className="font-medium">{acc.employee_name}</TableCell>
                <TableCell>{acc.email}</TableCell>
                <TableCell>{acc.department_name || '—'}</TableCell>
                <TableCell>{acc.position_title || '—'}</TableCell>
                <TableCell>
                  <code className="bg-muted px-2 py-1 rounded text-sm">{acc.username}</code>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <code className="bg-muted px-2 py-1 rounded text-sm">
                      {visiblePasswords[acc.id] ? acc.initial_password : '••••••••'}
                    </code>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => togglePasswordVisibility(acc.id)}
                    >
                      {visiblePasswords[acc.id] ? (
                        <EyeOff className="h-3.5 w-3.5" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={acc.is_active ? 'default' : 'secondary'}>
                    {acc.is_active
                      ? t('hr.pages.accounts.active')
                      : t('hr.pages.accounts.inactive')}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <Button size="sm" variant="outline" onClick={() => openEdit(acc)}>
                      {t('hr.common.edit')}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => resetMutation.mutate(acc.id)}
                      disabled={resetMutation.isPending}
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                      {t('hr.pages.accounts.resetPassword')}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyCredentials(acc)}
                    >
                      {copiedId === acc.id ? (
                        <Check className="h-3.5 w-3.5 mr-1" />
                      ) : (
                        <Copy className="h-3.5 w-3.5 mr-1" />
                      )}
                      {copiedId === acc.id
                        ? t('hr.pages.accounts.copied')
                        : t('hr.pages.accounts.copy')}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {(accounts || []).length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  {t('hr.pages.accounts.empty')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('hr.pages.accounts.editTitle')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">{t('hr.pages.accounts.fields.employee')}</label>
              <p className="text-sm text-muted-foreground">{editAccount?.employee_name}</p>
            </div>
            <div>
              <label className="text-sm font-medium">{t('hr.pages.accounts.fields.username')}</label>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t('hr.pages.accounts.fields.password')}</label>
              <Input
                value={form.initial_password}
                onChange={(e) => setForm({ ...form, initial_password: e.target.value })}
              />
              <p className="text-xs text-muted-foreground mt-1">
                {t('hr.pages.accounts.passwordHint')}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="rounded border-gray-300"
              />
              <label htmlFor="is_active" className="text-sm font-medium">
                {t('hr.pages.accounts.fields.isActive')}
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              {t('hr.common.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? t('hr.common.saving') : t('hr.common.save')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </HRLayout>
  );
};

export default HRAccounts;
