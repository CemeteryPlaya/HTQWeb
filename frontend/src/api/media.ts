import api from './client';

export const mediaApi = {
  upload: (file: File, isPublic = false) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_public', String(isPublic));
    return api.post('media/v1/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  download: (fileId: string) => api.get(`media/v1/${fileId}`, { responseType: 'blob' }),
  delete: (fileId: string) => api.delete(`media/v1/${fileId}`),
};
