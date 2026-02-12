import { useState } from 'react';
import axios from 'axios';
import api from '@/api/client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';

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

  const save = async () => {
    try {
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
  };

  return (
    <div className="container-custom py-12">
      <h1 className="font-display text-3xl mb-6">Управление новостями (скелет)</h1>
      <div className="mb-6">
        <Button onClick={() => setEditing(null)}>Создать новость</Button>
      </div>

      <div className="grid gap-4">
        {isLoading && <div>Loading...</div>}
        {!isLoading && data?.length === 0 && <div>Новости не найдены</div>}
        {!isLoading && data?.map((n: any) => (
          <div key={n.id} className="p-4 bg-card rounded-lg flex items-center justify-between">
            <div>
              <div className="font-semibold">{n.title}</div>
              <div className="text-sm text-muted-foreground">{n.slug} — {n.published ? 'Опубликовано' : 'Черновик'}</div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => startEdit(n)}>Редактировать</Button>
            </div>
          </div>
        ))}
      </div>

      {/* Editor */}
      <div className="mt-8 bg-background p-6 rounded-lg">
        <h2 className="font-semibold mb-4">{editing ? 'Редактирование' : 'Создать'}</h2>
        <div className="grid gap-3">
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Заголовок" className="p-3 rounded border" />
          <input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} placeholder="slug" className="p-3 rounded border" />
          <input value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} placeholder="Краткое описание" className="p-3 rounded border" />
          <textarea value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="Контент" className="p-3 rounded border" rows={6} />
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.published} onChange={(e) => setForm({ ...form, published: e.target.checked })} /> Опубликовано</label>
          <input type="file" onChange={(e: any) => setForm({ ...form, image: e.target.files?.[0] })} />
          <div className="flex gap-2">
            <Button onClick={save}>Сохранить</Button>
            <Button onClick={() => { setEditing(null); setForm({ title: '', slug: '', summary: '', content: '', published: false, image: null }); }}>Отмена</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminNews;
