import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

interface UserProfile {
  id: number;
  email: string;
  firstName: string;
  lastName: string;
  display_name: string;
  bio: string;
  avatarUrl?: string;
  roles: string[];
  settings: {
    language?: string;
    timezone?: string;
  };
  created_at: string;
  updated_at: string;
}

const HRProfiles = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [editProfile, setEditProfile] = useState<UserProfile | null>(null);
  const [form, setForm] = useState({
    display_name: '',
    bio: '',
    language: '',
    timezone: '',
  });
  const [search, setSearch] = useState('');

  const { data: profiles, isLoading, error } = useQuery({
    queryKey: ['hr-profiles'],
    queryFn: async () => {
      const res = await api.get('v1/profile/');
      return res.data as UserProfile[];
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => {
      const res = await api.patch(`v1/profile/${id}/`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-profiles'] });
      setEditOpen(false);
    },
  });

  const openEdit = (profile: UserProfile) => {
    setEditProfile(profile);
    setForm({
      display_name: profile.display_name || '',
      bio: profile.bio || '',
      language: profile.settings?.language || '',
      timezone: profile.settings?.timezone || '',
    });
    setEditOpen(true);
  };

  const handleSave = () => {
    if (!editProfile) return;
    updateMutation.mutate({
      id: editProfile.id,
      data: {
        display_name: form.display_name,
        bio: form.bio,
        settings: JSON.stringify({
          language: form.language,
          timezone: form.timezone,
        }),
      },
    });
  };

  const filtered = (profiles || []).filter((p) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.display_name?.toLowerCase().includes(q) ||
      p.email?.toLowerCase().includes(q) ||
      p.firstName?.toLowerCase().includes(q) ||
      p.lastName?.toLowerCase().includes(q)
    );
  });

  if (isLoading) return <HRLayout title={t('hr.pages.profiles.title')}><div className="p-8">{t('hr.common.loading')}</div></HRLayout>;
  if (error) return <HRLayout title={t('hr.pages.profiles.title')}><div className="p-8 text-red-500">{t('hr.common.error')}</div></HRLayout>;

  return (
    <HRLayout title={t('hr.pages.profiles.title')}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h2 className="text-2xl font-bold">{t('hr.pages.profiles.title')}</h2>
      </div>

      <div className="mb-4">
        <Input
          placeholder={t('hr.common.search')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
      </div>

      <div className="border rounded-lg overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('hr.pages.profiles.name')}</TableHead>
              <TableHead>{t('hr.pages.profiles.email')}</TableHead>
              <TableHead>{t('hr.pages.profiles.displayName')}</TableHead>
              <TableHead>{t('hr.pages.profiles.roles')}</TableHead>
              <TableHead>{t('hr.pages.profiles.language')}</TableHead>
              <TableHead>{t('hr.pages.profiles.timezone')}</TableHead>
              <TableHead>{t('hr.common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((profile) => (
              <TableRow key={profile.id}>
                <TableCell className="font-medium">
                  {profile.firstName} {profile.lastName}
                </TableCell>
                <TableCell>{profile.email}</TableCell>
                <TableCell>{profile.display_name}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {profile.roles.map((role) => (
                      <Badge key={role} variant="secondary">{role}</Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{profile.settings?.language || '—'}</TableCell>
                <TableCell>{profile.settings?.timezone || '—'}</TableCell>
                <TableCell>
                  <Button size="sm" variant="outline" onClick={() => openEdit(profile)}>
                    {t('hr.common.edit')}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  {t('hr.common.noData')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('hr.pages.profiles.editProfile')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">{t('hr.pages.profiles.userInfo')}</label>
              <p className="text-sm text-muted-foreground">
                {editProfile?.firstName} {editProfile?.lastName} — {editProfile?.email}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">{t('hr.pages.profiles.displayName')}</label>
              <Input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t('hr.pages.profiles.bio')}</label>
              <Textarea
                value={form.bio}
                onChange={(e) => setForm({ ...form, bio: e.target.value })}
                className="min-h-[100px]"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">{t('hr.pages.profiles.language')}</label>
                <Input
                  value={form.language}
                  onChange={(e) => setForm({ ...form, language: e.target.value })}
                  placeholder="ru"
                />
              </div>
              <div>
                <label className="text-sm font-medium">{t('hr.pages.profiles.timezone')}</label>
                <Input
                  value={form.timezone}
                  onChange={(e) => setForm({ ...form, timezone: e.target.value })}
                  placeholder="UTC+5"
                />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              {t('hr.common.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {t('hr.common.save')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </HRLayout>
  );
};

export default HRProfiles;
