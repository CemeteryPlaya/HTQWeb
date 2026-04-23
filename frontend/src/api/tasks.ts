/* ------------------------------------------------------------------ */
/*  Tasks module — API helpers                                         */
/* ------------------------------------------------------------------ */
import api from '@/api/client';
import type {
  Label, ProjectVersion, Task, TaskComment, TaskAttachment, TaskStats, TaskStatus,
  TaskLink, Notification
} from '@/types/tasks';

const BASE = 'tasks/v1/';

/* Unwrap paginated or plain array response */
function unwrap<T>(data: any): T[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/* ---------- Labels ---------- */
export const fetchLabels = async (): Promise<Label[]> => {
  const res = await api.get(`${BASE}labels/`);
  return unwrap<Label>(res.data);
};

export const createLabel = async (data: Partial<Label>): Promise<Label> => {
  const res = await api.post(`${BASE}labels/`, data);
  return res.data;
};

export const updateLabel = async (id: number, data: Partial<Label>): Promise<Label> => {
  const res = await api.patch(`${BASE}labels/${id}/`, data);
  return res.data;
};

export const deleteLabel = async (id: number): Promise<void> => {
  await api.delete(`${BASE}labels/${id}/`);
};

/* ---------- Project Versions ---------- */
export const fetchVersions = async (params?: Record<string, string>): Promise<ProjectVersion[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${BASE}versions/${query}`);
  return unwrap<ProjectVersion>(res.data);
};

export const fetchVersion = async (id: number): Promise<ProjectVersion> => {
  const res = await api.get(`${BASE}versions/${id}/`);
  return res.data;
};

export const createVersion = async (data: Partial<ProjectVersion>): Promise<ProjectVersion> => {
  const res = await api.post(`${BASE}versions/`, data);
  return res.data;
};

export const updateVersion = async (id: number, data: Partial<ProjectVersion>): Promise<ProjectVersion> => {
  const res = await api.patch(`${BASE}versions/${id}/`, data);
  return res.data;
};

export const deleteVersion = async (id: number): Promise<void> => {
  await api.delete(`${BASE}versions/${id}/`);
};

export const fetchVersionTasks = async (id: number): Promise<Task[]> => {
  const res = await api.get(`${BASE}versions/${id}/tasks/`);
  return Array.isArray(res.data) ? res.data : [];
};

/* ---------- Tasks ---------- */
export const fetchTasks = async (params?: Record<string, string>): Promise<Task[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${BASE}tasks/${query}`);
  return unwrap<Task>(res.data);
};

export const fetchTask = async (id: number): Promise<Task> => {
  const res = await api.get<Task>(`${BASE}tasks/${id}/`);
  return res.data;
};

export const fetchTaskTransitions = async (id: number): Promise<TaskStatus[]> => {
  const res = await api.get<TaskStatus[]>(`${BASE}tasks/${id}/transitions/`);
  return res.data;
};

export const createTask = async (data: Partial<Task>): Promise<Task> => {
  const res = await api.post(`${BASE}tasks/`, data);
  return res.data;
};

export const updateTask = async (id: number, data: Partial<Task>): Promise<Task> => {
  const res = await api.patch(`${BASE}tasks/${id}/`, data);
  return res.data;
};

export const deleteTask = async (id: number): Promise<void> => {
  await api.delete(`${BASE}tasks/${id}/`);
};

export const fetchTaskStats = async (params?: Record<string, string>): Promise<TaskStats> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${BASE}tasks/stats/${query}`);
  return res.data;
};

export const addTaskComment = async (taskId: number, body: string): Promise<TaskComment> => {
  const res = await api.post(`${BASE}tasks/${taskId}/comments/`, { body });
  return res.data;
};

export const addTaskAttachment = async (taskId: number, file: File): Promise<TaskAttachment> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post(`${BASE}tasks/${taskId}/attachments/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};
/* ---------- Task Links ---------- */
export const createTaskLink = async (data: { source: number; target: number; link_type: string }): Promise<TaskLink> => {
  const res = await api.post(`${BASE}task-links/`, data);
  return res.data;
};

export const deleteTaskLink = async (id: number): Promise<void> => {
  await api.delete(`${BASE}task-links/${id}/`);
};

/* ---------- Notifications ---------- */
export const fetchNotifications = async (): Promise<Notification[]> => {
  const res = await api.get(`${BASE}notifications/`);
  return unwrap<Notification>(res.data);
};

export const markNotificationRead = async (id: number): Promise<void> => {
  await api.post(`${BASE}notifications/${id}/mark_read/`);
};

export const markAllNotificationsRead = async (): Promise<void> => {
  await api.post(`${BASE}notifications/mark-all-read/`);
};
