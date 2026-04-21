import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';

interface ShareLink {
  id: string;
  token: string;
  label: string | null;
  max_level: number;
  link_type: string;
  expires_at: string | null;
  opened_at: string | null;
  is_active: boolean;
  created_at: string;
}

const TYPE_LABELS: Record<string, string> = {
  one_time: 'Одноразовая',
  time_limited: 'По времени',
  permanent_with_expiry: 'Постоянная с датой',
};

function LinkRow({ link, onRevoke }: { link: ShareLink; onRevoke: () => void }) {
  const [copied, setCopied] = useState(false);
  const publicUrl = `${window.location.origin}/public/org/${link.token}`;

  const copy = () => {
    navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`rounded-xl border bg-card px-4 py-3 ${!link.is_active ? 'opacity-50' : ''}`}>
      <div className="flex flex-wrap items-start gap-2 justify-between">
        <div className="min-w-0">
          <p className="font-medium text-sm truncate">{link.label || '(без названия)'}</p>
          <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">{publicUrl}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge variant="outline" className="text-xs">{TYPE_LABELS[link.link_type] ?? link.link_type}</Badge>
          <Badge variant={link.is_active ? 'default' : 'secondary'} className="text-xs">
            {link.opened_at ? 'Открыта' : link.is_active ? 'Активна' : 'Отозвана'}
          </Badge>
        </div>
      </div>
      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
        <span>Уровней: до {link.max_level}</span>
        {link.expires_at && <span>Истекает: {new Date(link.expires_at).toLocaleDateString('ru')}</span>}
        {link.opened_at && <span>Открыта: {new Date(link.opened_at).toLocaleString('ru')}</span>}
        <span>Создана: {new Date(link.created_at).toLocaleDateString('ru')}</span>
      </div>
      <div className="flex gap-2 mt-3">
        <Button size="sm" variant="outline" onClick={copy}>{copied ? 'Скопировано!' : 'Копировать ссылку'}</Button>
        {link.is_active && !link.opened_at && (
          <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={onRevoke}>
            Отозвать
          </Button>
        )}
      </div>
    </div>
  );
}

const HRShareLinks = () => {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({
    label: '',
    max_level: '3',
    link_type: 'one_time',
    expires_at: '',
  });

  const { data: links = [], isLoading } = useQuery<ShareLink[]>({
    queryKey: ['hr-share-links'],
    queryFn: async () => (await api.get('hr/v1/share-links/')).data,
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('hr/v1/share-links/', {
      label: form.label || null,
      max_level: parseInt(form.max_level),
      link_type: form.link_type,
      expires_at: form.expires_at || null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-share-links'] });
      setCreateOpen(false);
      setForm({ label: '', max_level: '3', link_type: 'one_time', expires_at: '' });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api.delete(`hr/v1/share-links/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-share-links'] }),
  });

  const activeLinks = links.filter((l) => l.is_active);
  const usedLinks = links.filter((l) => !l.is_active);

  return (
    <HRLayout title="Общий доступ" subtitle="Одноразовые ссылки на структуру компании для внешних пользователей">
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-muted-foreground">Активных: {activeLinks.length}</p>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>+ Создать ссылку</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Новая ссылка доступа</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <label className="grid gap-2 text-sm">
                Описание (для кого)
                <Input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} placeholder="Например: Заказчик ООО Ромашка" />
              </label>
              <label className="grid gap-2 text-sm">
                Максимальный уровень (1–10)
                <Input type="number" min={1} max={10} value={form.max_level} onChange={(e) => setForm({ ...form, max_level: e.target.value })} />
                <span className="text-xs text-muted-foreground">Заказчик увидит структуру до этого уровня включительно</span>
              </label>
              <label className="grid gap-2 text-sm">
                Тип ссылки
                <Select value={form.link_type} onValueChange={(v) => setForm({ ...form, link_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="one_time">Одноразовая (инвалидируется после открытия)</SelectItem>
                    <SelectItem value="time_limited">По времени (только с датой истечения)</SelectItem>
                    <SelectItem value="permanent_with_expiry">Постоянная с датой истечения</SelectItem>
                  </SelectContent>
                </Select>
              </label>
              {form.link_type !== 'one_time' && (
                <label className="grid gap-2 text-sm">
                  Дата истечения
                  <Input type="datetime-local" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} />
                </label>
              )}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setCreateOpen(false)}>Отмена</Button>
                <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Создание…' : 'Создать'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground text-center py-12">Загрузка…</div>
      ) : (
        <div className="space-y-6">
          {activeLinks.length > 0 && (
            <section>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">Активные</h3>
              <div className="space-y-3">
                {activeLinks.map((l) => (
                  <LinkRow key={l.id} link={l} onRevoke={() => revokeMutation.mutate(l.id)} />
                ))}
              </div>
            </section>
          )}
          {usedLinks.length > 0 && (
            <section>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">История</h3>
              <div className="space-y-3">
                {usedLinks.map((l) => (
                  <LinkRow key={l.id} link={l} onRevoke={() => {}} />
                ))}
              </div>
            </section>
          )}
          {links.length === 0 && (
            <div className="text-center py-16 text-muted-foreground text-sm">
              Ссылок ещё нет. Создайте первую.
            </div>
          )}
        </div>
      )}
    </HRLayout>
  );
};

export default HRShareLinks;
