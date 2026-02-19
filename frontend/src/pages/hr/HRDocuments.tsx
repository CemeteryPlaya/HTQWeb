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

interface Document {
  id: number;
  employee: number;
  employee_name: string;
  title: string;
  doc_type: string;
  file: string;
  uploaded_by_name: string;
  created_at: string;
  description?: string;
}

interface EmployeeOption {
  id: number;
  full_name: string;
}

const HRDocuments = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: documents, isLoading, error } = useQuery({
    queryKey: ['hr-documents'],
    queryFn: async () => {
      const res = await api.get<Document[]>('hr/documents/');
      return res.data;
    },
  });

  const { data: employees } = useQuery({
    queryKey: ['hr-employees'],
    queryFn: async () => {
      const res = await api.get<EmployeeOption[]>('hr/employees/');
      return res.data;
    },
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Document | null>(null);
  const [form, setForm] = useState({
    employee: 'none',
    title: '',
    doc_type: 'other',
    description: '',
    file: null as File | null,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      if (form.employee !== 'none') formData.append('employee', form.employee);
      formData.append('title', form.title);
      formData.append('doc_type', form.doc_type);
      formData.append('description', form.description || '');
      if (form.file) formData.append('file', form.file);

      if (editing) {
        const res = await api.put(`hr/documents/${editing.id}/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        return res.data;
      }
      const res = await api.post('hr/documents/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-documents'] });
      setDialogOpen(false);
      setEditing(null);
      setForm({ employee: 'none', title: '', doc_type: 'other', description: '', file: null });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`hr/documents/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hr-documents'] }),
  });

  const startCreate = () => {
    setEditing(null);
    setForm({ employee: 'none', title: '', doc_type: 'other', description: '', file: null });
    setDialogOpen(true);
  };

  const startEdit = (doc: Document) => {
    setEditing(doc);
    setForm({
      employee: doc.employee ? String(doc.employee) : 'none',
      title: doc.title || '',
      doc_type: doc.doc_type || 'other',
      description: doc.description || '',
      file: null,
    });
    setDialogOpen(true);
  };

  const docTypeLabels: Record<string, string> = {
    contract: t('hr.pages.documents.docTypes.contract'),
    amendment: t('hr.pages.documents.docTypes.amendment'),
    order: t('hr.pages.documents.docTypes.order'),
    certificate: t('hr.pages.documents.docTypes.certificate'),
    other: t('hr.pages.documents.docTypes.other'),
  };

  if (isLoading) {
    return (
      <HRLayout title={t('hr.pages.documents.title')} subtitle={t('hr.pages.documents.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center">{t('hr.common.loading')}</div>
      </HRLayout>
    );
  }
  if (error) {
    return (
      <HRLayout title={t('hr.pages.documents.title')} subtitle={t('hr.pages.documents.subtitle')}>
        <div className="rounded-2xl border bg-card/70 p-8 text-center text-red-500">
          {t('hr.pages.documents.error')}
        </div>
      </HRLayout>
    );
  }

  return (
    <HRLayout title={t('hr.pages.documents.title')} subtitle={t('hr.pages.documents.subtitle')}>
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">{t('hr.common.total')}: {documents?.length || 0}</div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={startCreate}>{t('hr.pages.documents.upload')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editing ? t('hr.pages.documents.edit') : t('hr.pages.documents.new')}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <label className="grid gap-2 text-sm">
                {t('hr.pages.documents.fields.employee')}
                <Select value={form.employee} onValueChange={(value) => setForm({ ...form, employee: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('hr.pages.documents.placeholders.selectEmployee')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t('hr.pages.documents.placeholders.selectEmployee')}</SelectItem>
                    {employees?.map((emp) => (
                      <SelectItem key={emp.id} value={String(emp.id)}>
                        {emp.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.documents.fields.title')}
                  <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </label>
                <label className="grid gap-2 text-sm">
                  {t('hr.pages.documents.fields.type')}
                  <Select value={form.doc_type} onValueChange={(value) => setForm({ ...form, doc_type: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('hr.pages.documents.placeholders.selectType')} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="contract">{t('hr.pages.documents.docTypes.contract')}</SelectItem>
                      <SelectItem value="amendment">{t('hr.pages.documents.docTypes.amendment')}</SelectItem>
                      <SelectItem value="order">{t('hr.pages.documents.docTypes.order')}</SelectItem>
                      <SelectItem value="certificate">{t('hr.pages.documents.docTypes.certificate')}</SelectItem>
                      <SelectItem value="other">{t('hr.pages.documents.docTypes.other')}</SelectItem>
                    </SelectContent>
                  </Select>
                </label>
              </div>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.documents.fields.description')}
                <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </label>

              <label className="grid gap-2 text-sm">
                {t('hr.pages.documents.fields.file')}
                <Input type="file" onChange={(e: any) => setForm({ ...form, file: e.target.files?.[0] || null })} />
              </label>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>{t('hr.common.cancel')}</Button>
                <Button onClick={() => saveMutation.mutate()} disabled={form.employee === 'none' || !form.title || saveMutation.isPending}>
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
              <TableHead>{t('hr.pages.documents.table.employee')}</TableHead>
              <TableHead>{t('hr.pages.documents.table.document')}</TableHead>
              <TableHead>{t('hr.pages.documents.table.type')}</TableHead>
              <TableHead>{t('hr.pages.documents.table.uploadedBy')}</TableHead>
              <TableHead>{t('hr.pages.documents.table.date')}</TableHead>
              <TableHead>{t('hr.pages.documents.table.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents?.map((doc) => (
              <TableRow key={doc.id}>
                <TableCell className="font-medium">{doc.employee_name}</TableCell>
                <TableCell>{doc.title}</TableCell>
                <TableCell>{docTypeLabels[doc.doc_type] || doc.doc_type}</TableCell>
                <TableCell>{doc.uploaded_by_name || '—'}</TableCell>
                <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <a href={doc.file} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      {t('hr.common.download')}
                    </a>
                    <Button size="sm" variant="outline" onClick={() => startEdit(doc)}>{t('hr.common.edit')}</Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm(t('hr.pages.documents.deleteConfirm')))
                        {
                          deleteMutation.mutate(doc.id);
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

export default HRDocuments;
