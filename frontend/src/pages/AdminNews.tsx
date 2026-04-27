import { useEffect, useState } from 'react';
import api from '@/api/client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Header } from '@/components/Header';

import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const fetchNews = async () => {
  const res = await api.get('cms/v1/news/');
  // Tolerate either a plain list or a paginated envelope.
  const data = res.data as unknown;
  if (Array.isArray(data)) return data;
  if (data && Array.isArray((data as any).items)) return (data as any).items;
  return [] as any[];
};

const AdminNews = () => {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ['newsList'],
    queryFn: fetchNews,
  });
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState<any>({ title: '', slug: '', summary: '', content: '', published: false, image: null });
  const [statusFilter, setStatusFilter] = useState<'all' | 'published' | 'draft'>('all');
  const [query, setQuery] = useState('');
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const newsList = Array.isArray(data) ? data : [];
  const publishedCount = newsList.filter((item) => item.published).length;
  const draftCount = newsList.length - publishedCount;

  const filteredNews = newsList.filter((item) => {
    const matchesQuery = `${item.title} ${item.slug}`.toLowerCase().includes(query.trim().toLowerCase());
    const matchesStatus = statusFilter === 'all'
      ? true
      : statusFilter === 'published'
        ? item.published
        : !item.published;
    return matchesQuery && matchesStatus;
  });

  const save = async () => {
    try {
      setSaving(true);

      // Upload the cover image (if any) through media-service first; backend
      // News.image is a string URL, not a file. Skip silently if no image.
      let imageUrl: string | undefined = imagePreview && imagePreview.startsWith('/') ? imagePreview : undefined;
      if (form.image instanceof File) {
        const fd = new FormData();
        fd.append('file', form.image);
        const upload = await api.post<{ url?: string; path?: string }>('media/v1/files/', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        imageUrl = (upload.data as any).url || (upload.data as any).path;
      }

      const payload: Record<string, unknown> = {
        title: form.title,
        slug: form.slug,
        summary: form.summary || '',
        content: form.content || '',
        published: !!form.published,
      };
      if (imageUrl) payload.image = imageUrl;

      if (editing) {
        await api.patch(`cms/v1/news/${editing.id}`, payload);
      } else {
        await api.post('cms/v1/news/', payload);
      }
      queryClient.invalidateQueries({ queryKey: ['newsList'] });
      setEditing(null);
      setForm({ title: '', slug: '', summary: '', content: '', published: false, image: null });
      setImagePreview(null);
      setIsDialogOpen(false);
    } catch (err: any) {
      console.error(err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || err?.response?.data || err?.message;
      if (status === 401) {
        alert('Неавторизован. Выполните вход.');
      } else if (status === 403) {
        alert(`Доступ запрещён (403). Убедитесь, что ваш пользователь имеет права staff/admin.`);
      } else {
        alert(`Ошибка при сохранении: ${detail || 'unknown error'}`);
      }
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item: any) => {
    setEditing(item);
    setForm({
      title: item.title,
      slug: item.slug,
      summary: item.summary || '',
      content: item.content || '',
      published: item.published,
      image: null,
    });
    setImagePreview(item.image || null);
    setIsDialogOpen(true);
  };

  const openCreateDialog = () => {
    setEditing(null);
    setForm({ title: '', slug: '', summary: '', content: '', published: false, image: null });
    setImagePreview(null);
    setIsDialogOpen(true);
  };

  const generateSlug = () => {
    const raw = form.title
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');
    setForm({ ...form, slug: raw });
  };

  useEffect(() => {
    if (!form.image) return;
    const url = URL.createObjectURL(form.image);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [form.image]);

  return (
    <div className="min-h-screen flex flex-col bg-[radial-gradient(circle_at_top,hsl(145_40%_96%),hsl(0_0%_100%)_55%)]">
      <Header />

      <main className="relative flex-1 overflow-hidden">
        <div className="pointer-events-none absolute -left-24 -top-20 h-72 w-72 rounded-full bg-[radial-gradient(circle,hsl(42_85%_70%/0.45),transparent_70%)]" />
        <div className="pointer-events-none absolute -right-20 top-32 h-96 w-96 rounded-full bg-[radial-gradient(circle,hsl(145_45%_40%/0.25),transparent_70%)]" />

        <div className="container-custom py-12 pb-24">
          <div className="mb-6 flex flex-col gap-4">
            <Link
              to="/myprofile"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
            >
              <ArrowLeft className="h-4 w-4" />
              {t('hr.backToMain', 'Назад в профиль')}
            </Link>
          </div>
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center lg:justify-between">
              <div>
                <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground">HR Management</div>
                <h1 className="font-display text-3xl sm:text-4xl font-semibold text-foreground">Manage news</h1>
                <p className="text-muted-foreground text-sm sm:text-base mt-2">Панель управления публикациями и карточками новостей.</p>
              </div>
              <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                <Button className="w-full sm:w-auto" onClick={openCreateDialog}>Новая новость</Button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border bg-card/80 p-5 shadow-[var(--shadow-soft)]">
                <div className="text-sm text-muted-foreground">Всего новостей</div>
                <div className="mt-2 text-3xl font-semibold">{newsList.length}</div>
              </div>
              <div className="rounded-2xl border bg-card/80 p-5 shadow-[var(--shadow-soft)]">
                <div className="text-sm text-muted-foreground">Опубликовано</div>
                <div className="mt-2 text-3xl font-semibold text-primary">{publishedCount}</div>
              </div>
              <div className="rounded-2xl border bg-card/80 p-5 shadow-[var(--shadow-soft)]">
                <div className="text-sm text-muted-foreground">Черновики</div>
                <div className="mt-2 text-3xl font-semibold text-secondary-foreground">{draftCount}</div>
              </div>
            </div>

            <div className="rounded-2xl border bg-card/70 p-4 shadow-[var(--shadow-soft)]">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex flex-1 flex-wrap items-center gap-3">
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Поиск по заголовку или slug"
                    className="md:max-w-sm"
                  />
                  <div className="flex flex-wrap items-center gap-2 rounded-2xl border bg-background px-3 py-2 text-sm">
                    <button
                      className={`rounded-full px-3 py-1 ${statusFilter === 'all' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
                      onClick={() => setStatusFilter('all')}
                    >
                      Все
                    </button>
                    <button
                      className={`rounded-full px-3 py-1 ${statusFilter === 'published' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
                      onClick={() => setStatusFilter('published')}
                    >
                      Опубликовано
                    </button>
                    <button
                      className={`rounded-full px-3 py-1 ${statusFilter === 'draft' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
                      onClick={() => setStatusFilter('draft')}
                    >
                      Черновики
                    </button>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  Показано: <span className="text-foreground">{filteredNews.length}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 space-y-4">
            {isLoading && <div className="rounded-2xl border bg-card/70 p-6">Загрузка...</div>}
            {!isLoading && filteredNews.length === 0 && (
              <div className="rounded-2xl border bg-card/70 p-8 text-center">
                <div className="text-lg font-semibold">Новости не найдены</div>
                <p className="text-muted-foreground">Попробуйте изменить фильтры или создайте новую новость.</p>
                <Button className="mt-4" onClick={openCreateDialog}>Создать новость</Button>
              </div>
            )}
            {!isLoading && filteredNews.map((item: any) => (
              <div key={item.id} className="group rounded-2xl border bg-card/70 p-5 transition-all hover:-translate-y-1 hover:shadow-[var(--shadow-card)]">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-start gap-4 overflow-hidden w-full md:w-auto">
                    <div className="shrink-0 h-16 w-16 overflow-hidden rounded-xl bg-muted">
                      {item.image ? (
                        <img src={item.image} alt={item.title} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">No image</div>
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <h2 className="text-base sm:text-lg font-semibold text-foreground truncate max-w-full">{item.title}</h2>
                        <Badge variant={item.published ? 'default' : 'outline'} className="shrink-0">
                          {item.published ? 'Опубликовано' : 'Черновик'}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">{item.slug}</div>
                      {item.published_at && (
                        <div className="text-xs text-muted-foreground">{new Date(item.published_at).toLocaleString()}</div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={() => startEdit(item)}>Редактировать</Button>
                    <a href={`/news/${item.slug}`} className="inline-flex items-center rounded-md border px-4 py-2 text-sm transition hover:bg-accent">Просмотр</a>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogContent className="w-[95vw] sm:max-w-2xl max-h-[90vh] overflow-y-auto p-4 sm:p-6 rounded-2xl">
              <DialogHeader>
                <div className="flex flex-wrap items-center justify-between gap-2 sm:pr-6">
                  <DialogTitle className="text-xl sm:text-2xl font-semibold">
                    {editing ? 'Редактирование новости' : 'Карточка новости'}
                  </DialogTitle>
                  <Badge variant={form.published ? 'default' : 'outline'}>
                    {form.published ? 'Публично' : 'Черновик'}
                  </Badge>
                </div>
              </DialogHeader>

              <div className="mt-2 grid gap-4">
                <label className="grid gap-2 text-sm">
                  Заголовок
                  <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Новая новость" />
                </label>

                <div className="grid gap-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Slug</span>
                    <button className="text-xs text-primary" onClick={generateSlug}>Сгенерировать</button>
                  </div>
                  <Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} placeholder="news-title" />
                </div>

                <label className="grid gap-2 text-sm">
                  Краткое описание
                  <textarea
                    value={form.summary}
                    onChange={(e) => setForm({ ...form, summary: e.target.value })}
                    placeholder="Короткий анонс для карточки"
                    className="min-h-[90px] rounded-md border border-input bg-background p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>

                <label className="grid gap-2 text-sm">
                  Контент
                  <textarea
                    value={form.content}
                    onChange={(e) => setForm({ ...form, content: e.target.value })}
                    placeholder="Основной текст или HTML контент"
                    className="min-h-[160px] rounded-md border border-input bg-background p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>

                <div className="flex items-center justify-between rounded-xl border bg-background px-3 py-3">
                  <div>
                    <div className="text-sm font-medium">Публикация</div>
                    <div className="text-xs text-muted-foreground">Показать новость на сайте</div>
                  </div>
                  <button
                    className={`relative h-7 w-12 rounded-full transition ${form.published ? 'bg-primary' : 'bg-muted'}`}
                    onClick={() => setForm({ ...form, published: !form.published })}
                  >
                    <span
                      className={`absolute left-1 top-1 h-5 w-5 rounded-full bg-white transition ${form.published ? 'translate-x-5' : ''}`}
                    />
                  </button>
                </div>

                <div className="grid gap-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Обложка</span>
                    {imagePreview && (
                      <button
                        className="text-xs text-muted-foreground"
                        onClick={() => {
                          setImagePreview(null);
                          setForm({ ...form, image: null });
                        }}
                      >
                        Очистить
                      </button>
                    )}
                  </div>
                  {imagePreview && (
                    <div className="overflow-hidden rounded-xl border bg-muted">
                      <img src={imagePreview} alt="Preview" className="h-40 w-full object-cover" />
                    </div>
                  )}
                  <Input type="file" onChange={(e: any) => setForm({ ...form, image: e.target.files?.[0] })} />
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  <Button onClick={save} disabled={saving || !form.title || !form.slug}>
                    {saving ? 'Сохранение...' : editing ? 'Сохранить изменения' : 'Создать новость'}
                  </Button>
                  <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Отмена</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </main>
    </div>
  );
};

export default AdminNews;
