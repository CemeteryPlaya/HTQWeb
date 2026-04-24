import api from '@/api/client';
import { CalendarEvent, ProductionDay, CalendarTimeline } from '@/types/calendar';

const HR = '';

export const fetchCalendarEvents = async (): Promise<CalendarEvent[]> => {
  try {
    const res = await api.get<any>(`${HR}calendar-events/`);
    const payload = res.data?.results ?? res.data;
    return Array.isArray(payload) ? payload : [];
  } catch {
    return [];
  }
};

export const createCalendarEvent = async (data: Partial<CalendarEvent>): Promise<CalendarEvent> => {
  const res = await api.post<CalendarEvent>(`${HR}calendar-events/`, data);
  return res.data;
};

export const updateCalendarEvent = async (id: number, data: Partial<CalendarEvent>): Promise<CalendarEvent> => {
  const res = await api.patch<CalendarEvent>(`${HR}calendar-events/${id}/`, data);
  return res.data;
};

export const deleteCalendarEvent = async (id: number): Promise<void> => {
  await api.delete(`${HR}calendar-events/${id}/`);
};

export const fetchProductionCalendar = async (start?: string, end?: string): Promise<ProductionDay[]> => {
  const params = new URLSearchParams();
  if (start) params.append('date__gte', start);
  if (end) params.append('date__lte', end);
  // Legacy path not yet ported — return empty list on any error.
  try {
    const res = await api.get<any>(`${HR}production-calendar/?${params.toString()}`);
    const payload = res.data?.results ?? res.data;
    return Array.isArray(payload) ? payload : [];
  } catch {
    return [];
  }
};

export const fetchCalendarTimeline = async (start?: string, end?: string): Promise<CalendarTimeline> => {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  // The legacy Django path `/api/calendar-timeline/` isn't yet ported to
  // task-service. Swallow transport/parse errors and return an empty
  // timeline — every consumer (ConferenceNotifier, CalendarWidget) is
  // mounted globally, so one failed request must not crash the SPA.
  try {
    const res = await api.get<CalendarTimeline>(`${HR}calendar-timeline/?${params.toString()}`);
    const payload = res.data ?? {};
    return {
      tasks: Array.isArray(payload.tasks) ? payload.tasks : [],
      events: Array.isArray(payload.events) ? payload.events : [],
    };
  } catch {
    return { tasks: [], events: [] };
  }
};

export const updateProductionDay = async (date: string, data: Partial<ProductionDay>): Promise<ProductionDay> => {
  const res = await api.patch<ProductionDay>(`${HR}production-calendar/${date}/`, data);
  return res.data;
};
