/* ------------------------------------------------------------------ */
/*  Tasks module — API helpers                                         */
/* ------------------------------------------------------------------ */
import api from '@/api/client';
import type {
  Label, ProjectVersion, Task, TaskComment, TaskAttachment, TaskStats, TaskStatus,
  TaskLink, Notification
} from '@/types/tasks';

const HR = '';

/* Unwrap paginated or plain array response */
function unwrap<T>(data: any): T[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/* ---------- Labels ---------- */
export const fetchLabels = async (): Promise<Label[]> => {
  const res = await api.get(`${HR}labels/`);
  return unwrap<Label>(res.data);
};

export const createLabel = async (data: Partial<Label>): Promise<Label> => {
  const res = await api.post(`${HR}labels/`, data);
  return res.data;
};

export const updateLabel = async (id: number, data: Partial<Label>): Promise<Label> => {
  const res = await api.patch(`${HR}labels/${id}/`, data);
  return res.data;
};

export const deleteLabel = async (id: number): Promise<void> => {
  await api.delete(`${HR}labels/${id}/`);
};

/* ---------- Project Versions ---------- */
export const fetchVersions = async (params?: Record<string, string>): Promise<ProjectVersion[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}versions/${query}`);
  return unwrap<ProjectVersion>(res.data);
};

export const fetchVersion = async (id: number): Promise<ProjectVersion> => {
  const res = await api.get(`${HR}versions/${id}/`);
  return res.data;
};

export const createVersion = async (data: Partial<ProjectVersion>): Promise<ProjectVersion> => {
  const res = await api.post(`${HR}versions/`, data);
  return res.data;
};

export const updateVersion = async (id: number, data: Partial<ProjectVersion>): Promise<ProjectVersion> => {
  const res = await api.patch(`${HR}versions/${id}/`, data);
  return res.data;
};

export const deleteVersion = async (id: number): Promise<void> => {
  await api.delete(`${HR}versions/${id}/`);
};

export const fetchVersionTasks = async (id: number): Promise<Task[]> => {
  const res = await api.get(`${HR}versions/${id}/tasks/`);
  return Array.isArray(res.data) ? res.data : [];
};

/* ---------- Tasks ---------- */
export const fetchTasks = async (params?: Record<string, string>): Promise<Task[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}tasks/${query}`);
  return unwrap<Task>(res.data);
};

export const fetchTask = async (id: number): Promise<Task> => {
  const res = await api.get<Task>(`${HR}tasks/${id}/`);
  return res.data;
};

export const fetchTaskTransitions = async (id: number): Promise<TaskStatus[]> => {
  const res = await api.get<TaskStatus[]>(`${HR}tasks/${id}/transitions/`);
  return res.data;
};

export const createTask = async (data: Partial<Task>): Promise<Task> => {
  const res = await api.post(`${HR}tasks/`, data);
  return res.data;
};

export const updateTask = async (id: number, data: Partial<Task>): Promise<Task> => {
  const res = await api.patch(`${HR}tasks/${id}/`, data);
  return res.data;
};

export const deleteTask = async (id: number): Promise<void> => {
  await api.delete(`${HR}tasks/${id}/`);
};

export const fetchTaskStats = async (params?: Record<string, string>): Promise<TaskStats> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}tasks/stats/${query}`);
  return res.data;
};

export const addTaskComment = async (taskId: number, body: string): Promise<TaskComment> => {
  const res = await api.post(`${HR}tasks/${taskId}/comments/`, { body });
  return res.data;
};

export const addTaskAttachment = async (taskId: number, file: File): Promise<TaskAttachment> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post(`${HR}tasks/${taskId}/attachments/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};
/* ---------- Task Links ---------- */
export const createTaskLink = async (data: { source: number; target: number; link_type: string }): Promise<TaskLink> => {
  const res = await api.post(`${HR}task-links/`, data);
  return res.data;
};

export const deleteTaskLink = async (id: number): Promise<void> => {
  await api.delete(`${HR}task-links/${id}/`);
};

/* ---------- Notifications ---------- */
export const fetchNotifications = async (): Promise<Notification[]> => {
  const res = await api.get(`${HR}notifications/`);
  return unwrap<Notification>(res.data);
};

export const markNotificationRead = async (id: number): Promise<void> => {
  await api.post(`${HR}notifications/${id}/mark_read/`);
};

export const markAllNotificationsRead = async (): Promise<void> => {
  await api.post(`${HR}notifications/mark-all-read/`);
};
