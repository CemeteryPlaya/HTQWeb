import api from './client';

export const cmsApi = {
  getNews: (params?: any) => api.get('cms/v1/news/', { params }),
  getNewsItem: (id: number) => api.get(`cms/v1/news/${id}/`),
  createContactRequest: (data: any) => api.post('cms/v1/contact-requests/', data),
  getConferenceConfig: () => api.get('cms/v1/conference/config'),
};
