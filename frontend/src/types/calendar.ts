import { Task } from './tasks';

export type CalendarEventType = 'common' | 'department' | 'personal' | 'conference';

export interface CalendarEvent {
  id: number;
  title: string;
  description: string;
  event_type: CalendarEventType;
  creator: number;
  creator_name: string;
  department?: number;
  department_name?: string;
  start_at: string;
  end_at: string;
  is_all_day: boolean;
  rrule?: string;
  conference_room_id?: string;
  exceptions?: EventException[];
  created_at: string;
  updated_at: string;
}

export interface EventException {
  id: number;
  event: number;
  original_date: string;
  is_cancelled: boolean;
  new_start_at?: string;
  new_end_at?: string;
}

export interface ProductionDay {
  date: string;
  day_type: 'working' | 'weekend' | 'holiday' | 'short';
  working_days_since_epoch: number;
  note?: string;
}

export interface CalendarTimeline {
  tasks: Task[];
  events: CalendarEvent[];
}
