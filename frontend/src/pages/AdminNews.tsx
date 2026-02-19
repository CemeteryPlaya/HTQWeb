import { useEffect, useMemo, useState } from 'react';
import api from '@/api/client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

const fetchNews = async () => {
  const res = await api.get('news/');
  return res.data;
};

const AdminNews = () => {
  const queryClient = useQueryClient();
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

  const newsList = Array.isArray(data) ? data : [];
  const publishedCount = newsList.filter((item) => item.published).length;
  const draftCount = newsList.length - publishedCount;

  const filteredNews = useMemo(() => {
    return newsList.filter((item) => {
      const matchesQuery = `${item.title} ${item.slug}`.toLowerCase().includes(query.trim().toLowerCase());
      const matchesStatus = statusFilter === 'all'
        ? true
        : statusFilter === 'published'
          ? item.published
          : !item.published;
      return matchesQuery && matchesStatus;
    });
  }, [newsList, query, statusFilter]);

  const save = async () => {
    try {
      setSaving(true);
      const formData = new FormData();
      formData.append('title', form.title);
      formData.append('slug', form.slug);
      formData.append('summary', form.summary || '');
      formData.append('content', form.content || '');
      formData.append('published', form.published ? 'true' : 'false');
      if (form.image) formData.append('image', form.image);

      if (editing) {
        await api.put(`news/${editing.slug}/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else {
        await api.post('news/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      }
      queryClient.invalidateQueries({ queryKey: ['newsList'] });
      setEditing(null);
      setForm({ title: '', slug: '', summary: '', content: '', published: false, image: null });
      setImagePreview(null);
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
  };

  const resetForm = () => {
    setEditing(null);
    setForm({ title: '', slug: '', summary: '', content: '', published: false, image: null });
    setImagePreview(null);
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
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,hsl(145_40%_96%),hsl(0_0%_100%)_55%)]">
      <div className="pointer-events-none absolute -left-24 -top-20 h-72 w-72 rounded-full bg-[radial-gradient(circle,hsl(42_85%_70%/0.45),transparent_70%)]" />
      <div className="pointer-events-none absolute -right-20 top-32 h-96 w-96 rounded-full bg-[radial-gradient(circle,hsl(145_45%_40%/0.25),transparent_70%)]" />

      <div className="container-custom py-12">
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground">HR Management</div>
              <h1 className="font-display text-4xl font-semibold text-foreground">Manage news</h1>
              <p className="text-muted-foreground">Панель управления публикациями и карточками новостей.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={resetForm}>Новая новость</Button>
              <Button onClick={save} disabled={saving || !form.title || !form.slug}>
                {saving ? 'Сохранение...' : editing ? 'Обновить' : 'Опубликовать'}
              </Button>
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
                <div className="flex items-center gap-2 rounded-full border bg-background px-3 py-1 text-sm">
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

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            {isLoading && <div className="rounded-2xl border bg-card/70 p-6">Загрузка...</div>}
            {!isLoading && filteredNews.length === 0 && (
              <div className="rounded-2xl border bg-card/70 p-8 text-center">
                <div className="text-lg font-semibold">Новости не найдены</div>
                <p className="text-muted-foreground">Попробуйте изменить фильтры или создайте новую новость.</p>
                <Button className="mt-4" onClick={resetForm}>Создать новость</Button>
              </div>
            )}
            {!isLoading && filteredNews.map((item: any) => (
              <div key={item.id} className="group rounded-2xl border bg-card/70 p-5 transition-all hover:-translate-y-1 hover:shadow-[var(--shadow-card)]">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-start gap-4">
                    <div className="h-16 w-16 overflow-hidden rounded-xl bg-muted">
                      {item.image ? (
                        <img src={item.image} alt={item.title} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">No image</div>
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-foreground">{item.title}</h3>
                        <Badge variant={item.published ? 'default' : 'outline'}>
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

          <div className="lg:sticky lg:top-6">
            <div className="rounded-2xl border bg-card/80 p-6 shadow-[var(--shadow-soft)]">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">{editing ? 'Редактирование' : 'Создание'}</div>
                  <h2 className="text-2xl font-semibold">Карточка новости</h2>
                </div>
                <Badge variant={form.published ? 'default' : 'outline'}>{form.published ? 'Публично' : 'Черновик'}</Badge>
              </div>

              <div className="mt-6 grid gap-4">
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
                  <Button variant="outline" onClick={resetForm}>Сбросить</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminNews;
