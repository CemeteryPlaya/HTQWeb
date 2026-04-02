/* ------------------------------------------------------------------ */
/*  Department File Manager — API helpers                              */
/* ------------------------------------------------------------------ */
import api from '@/api/client';
import type { DepartmentFolder, DepartmentFile } from '@/types/fileManager';

const HR = 'hr/';

/* Unwrap paginated or plain array response */
function unwrap<T>(data: any): T[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/* ---------- Folders ---------- */
export const fetchMyFolders = async (): Promise<DepartmentFolder[]> => {
  const res = await api.get(`${HR}department-folders/`);
  return unwrap<DepartmentFolder>(res.data);
};

export const fetchFolder = async (id: number): Promise<DepartmentFolder> => {
  const res = await api.get(`${HR}department-folders/${id}/`);
  return res.data;
};

/* ---------- Files ---------- */
export const fetchFolderFiles = async (folderId: number): Promise<DepartmentFile[]> => {
  const res = await api.get(`${HR}department-files/?folder=${folderId}`);
  return unwrap<DepartmentFile>(res.data);
};

export const uploadFile = async (
  folderId: number,
  file: File,
  description?: string,
): Promise<DepartmentFile> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('folder', String(folderId));
  formData.append('name', file.name);
  if (description) formData.append('description', description);

  const res = await api.post(`${HR}department-files/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const deleteFile = async (fileId: number): Promise<void> => {
  await api.delete(`${HR}department-files/${fileId}/`);
};

/* ---------- Download helper ---------- */
export const downloadFileUrl = (fileUrl: string): void => {
  const a = document.createElement('a');
  a.href = fileUrl;
  a.download = '';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};
