import api from '@/api/client';
import { CalendarEvent, ProductionDay, CalendarTimeline } from '@/types/calendar';

const HR = '';

export const fetchCalendarEvents = async (): Promise<CalendarEvent[]> => {
  const res = await api.get<any>(`${HR}calendar-events/`);
  return res.data.results || res.data;
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
  const res = await api.get<any>(`${HR}production-calendar/?${params.toString()}`);
  return res.data.results || res.data;
};

export const fetchCalendarTimeline = async (start?: string, end?: string): Promise<CalendarTimeline> => {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  const res = await api.get<CalendarTimeline>(`${HR}calendar-timeline/?${params.toString()}`);
  return res.data;
};

export const updateProductionDay = async (date: string, data: Partial<ProductionDay>): Promise<ProductionDay> => {
  const res = await api.patch<ProductionDay>(`${HR}production-calendar/${date}/`, data);
  return res.data;
};
