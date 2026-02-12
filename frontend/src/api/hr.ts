/* ------------------------------------------------------------------ */
/*  HR module — API helpers                                            */
/* ------------------------------------------------------------------ */
import api from '@/api/client';
import type {
  Department, Position, Employee, EmployeeStats, HRUserOption,
  Vacancy, Application, TimeRecord, HRDocument, HRActionLog,
} from '@/types/hr';

const HR = 'v1/hr/';

/* Unwrap paginated or plain array response */
function unwrap<T>(data: any): T[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/* ---------- Departments ---------- */
export const fetchDepartments = async (): Promise<Department[]> => {
  const res = await api.get(`${HR}departments/`);
  return unwrap<Department>(res.data);
};

export const createDepartment = async (data: Partial<Department>): Promise<Department> => {
  const res = await api.post(`${HR}departments/`, data);
  return res.data;
};

export const updateDepartment = async (id: number, data: Partial<Department>): Promise<Department> => {
  const res = await api.patch(`${HR}departments/${id}/`, data);
  return res.data;
};

export const deleteDepartment = async (id: number): Promise<void> => {
  await api.delete(`${HR}departments/${id}/`);
};

/* ---------- Positions ---------- */
export const fetchPositions = async (): Promise<Position[]> => {
  const res = await api.get(`${HR}positions/`);
  return unwrap<Position>(res.data);
};

export const createPosition = async (data: Partial<Position>): Promise<Position> => {
  const res = await api.post(`${HR}positions/`, data);
  return res.data;
};

export const updatePosition = async (id: number, data: Partial<Position>): Promise<Position> => {
  const res = await api.patch(`${HR}positions/${id}/`, data);
  return res.data;
};

export const deletePosition = async (id: number): Promise<void> => {
  await api.delete(`${HR}positions/${id}/`);
};

/* ---------- Employees ---------- */
export const fetchEmployees = async (params?: Record<string, string>): Promise<Employee[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}employees/${query}`);
  return unwrap<Employee>(res.data);
};

export const fetchEmployee = async (id: number): Promise<Employee> => {
  const res = await api.get(`${HR}employees/${id}/`);
  return res.data;
};

export const fetchEmployeeStats = async (): Promise<EmployeeStats> => {
  const res = await api.get(`${HR}employees/stats/`);
  return res.data;
};

export const fetchEmployeeUsers = async (params?: Record<string, string>): Promise<HRUserOption[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}employees/users/${query}`);
  return unwrap<HRUserOption>(res.data);
};

export const createEmployee = async (data: Partial<Employee>): Promise<Employee> => {
  const res = await api.post(`${HR}employees/`, data);
  return res.data;
};

export const updateEmployee = async (id: number, data: Partial<Employee>): Promise<Employee> => {
  const res = await api.patch(`${HR}employees/${id}/`, data);
  return res.data;
};

export const deleteEmployee = async (id: number): Promise<void> => {
  await api.delete(`${HR}employees/${id}/`);
};

/* ---------- Vacancies ---------- */
export const fetchVacancies = async (): Promise<Vacancy[]> => {
  const res = await api.get(`${HR}vacancies/`);
  return unwrap<Vacancy>(res.data);
};

export const createVacancy = async (data: Partial<Vacancy>): Promise<Vacancy> => {
  const res = await api.post(`${HR}vacancies/`, data);
  return res.data;
};

export const updateVacancy = async (id: number, data: Partial<Vacancy>): Promise<Vacancy> => {
  const res = await api.patch(`${HR}vacancies/${id}/`, data);
  return res.data;
};

export const deleteVacancy = async (id: number): Promise<void> => {
  await api.delete(`${HR}vacancies/${id}/`);
};

/* ---------- Applications ---------- */
export const fetchApplications = async (params?: Record<string, string>): Promise<Application[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}applications/${query}`);
  return unwrap<Application>(res.data);
};

export const createApplication = async (data: FormData): Promise<Application> => {
  const res = await api.post(`${HR}applications/`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const updateApplication = async (id: number, data: Partial<Application>): Promise<Application> => {
  const res = await api.patch(`${HR}applications/${id}/`, data);
  return res.data;
};

export const deleteApplication = async (id: number): Promise<void> => {
  await api.delete(`${HR}applications/${id}/`);
};

/* ---------- Time Tracking ---------- */
export const fetchTimeRecords = async (params?: Record<string, string>): Promise<TimeRecord[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}time-tracking/${query}`);
  return unwrap<TimeRecord>(res.data);
};

export const createTimeRecord = async (data: Partial<TimeRecord>): Promise<TimeRecord> => {
  const res = await api.post(`${HR}time-tracking/`, data);
  return res.data;
};

export const updateTimeRecord = async (id: number, data: Partial<TimeRecord>): Promise<TimeRecord> => {
  const res = await api.patch(`${HR}time-tracking/${id}/`, data);
  return res.data;
};

export const approveTimeRecord = async (id: number): Promise<TimeRecord> => {
  const res = await api.post(`${HR}time-tracking/${id}/approve/`);
  return res.data;
};

export const rejectTimeRecord = async (id: number): Promise<TimeRecord> => {
  const res = await api.post(`${HR}time-tracking/${id}/reject/`);
  return res.data;
};

export const deleteTimeRecord = async (id: number): Promise<void> => {
  await api.delete(`${HR}time-tracking/${id}/`);
};

/* ---------- Documents ---------- */
export const fetchDocuments = async (params?: Record<string, string>): Promise<HRDocument[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}documents/${query}`);
  return unwrap<HRDocument>(res.data);
};

export const uploadDocument = async (data: FormData): Promise<HRDocument> => {
  const res = await api.post(`${HR}documents/`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const deleteDocument = async (id: number): Promise<void> => {
  await api.delete(`${HR}documents/${id}/`);
};

/* ---------- Action Logs ---------- */
export const fetchActionLogs = async (params?: Record<string, string>): Promise<HRActionLog[]> => {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await api.get(`${HR}logs/${query}`);
  return unwrap<HRActionLog>(res.data);
};
