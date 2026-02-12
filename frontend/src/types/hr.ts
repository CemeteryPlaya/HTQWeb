/* ------------------------------------------------------------------ */
/*  HR module — shared types                                           */
/* ------------------------------------------------------------------ */

export interface Department {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export interface Position {
  id: number;
  title: string;
  department: number | null;
  department_name: string | null;
}

export type EmployeeStatus = 'active' | 'on_leave' | 'dismissed';

export interface Employee {
  id: number;
  user: number;
  full_name: string;
  username: string;
  email: string;
  position: number | null;
  position_title: string | null;
  department: number | null;
  department_name: string | null;
  phone: string;
  date_hired: string | null;
  date_dismissed: string | null;
  status: EmployeeStatus;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface EmployeeStats {
  total: number;
  active: number;
  on_leave: number;
  dismissed: number;
}

export interface HRUserOption {
  id: number;
  full_name: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
}

export type VacancyStatus = 'open' | 'closed' | 'on_hold';

export interface Vacancy {
  id: number;
  title: string;
  department: number | null;
  department_name: string | null;
  description: string;
  requirements: string;
  salary_min: string | null;
  salary_max: string | null;
  status: VacancyStatus;
  created_by: number | null;
  created_by_name: string | null;
  applications_count: number;
  created_at: string;
  updated_at: string;
}

export type ApplicationStatus = 'new' | 'reviewed' | 'interview' | 'offered' | 'rejected' | 'hired';

export interface Application {
  id: number;
  vacancy: number;
  vacancy_title: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  resume: string | null;
  cover_letter: string;
  status: ApplicationStatus;
  notes: string;
  created_at: string;
  updated_at: string;
}

export type LeaveType = 'vacation' | 'sick_leave' | 'day_off' | 'business_trip' | 'unpaid';
export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

export interface TimeRecord {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: LeaveStatus;
  comment: string;
  approved_by: number | null;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export type DocType = 'contract' | 'amendment' | 'order' | 'certificate' | 'other';

export interface HRDocument {
  id: number;
  employee: number;
  employee_name: string;
  title: string;
  doc_type: DocType;
  file: string;
  description: string;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  created_at: string;
}

/* ---------- Action Logs ---------- */
export type HRActionType = 'create' | 'update' | 'delete' | 'approve' | 'reject' | 'status_change';
export type HRTargetType = 'employee' | 'department' | 'position' | 'vacancy' | 'application' | 'time_tracking' | 'document';

export interface HRActionLog {
  id: number;
  user: number | null;
  user_name: string;
  employee: number | null;
  employee_name: string | null;
  department: number | null;
  department_name: string | null;
  position: number | null;
  position_title: string | null;
  action: HRActionType;
  target_type: HRTargetType;
  target_id: number | null;
  target_repr: string;
  details: string;
  ip_address: string | null;
  created_at: string;
}
