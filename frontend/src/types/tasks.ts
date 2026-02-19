/* ------------------------------------------------------------------ */
/*  Tasks module — shared types                                        */
/* ------------------------------------------------------------------ */

/* ---------- Labels ---------- */
export interface Label {
  id: number;
  name: string;
  color: string;
}

/* ---------- Project Versions (Roadmap) ---------- */
export type VersionStatus = 'planned' | 'in_progress' | 'released' | 'archived';

export interface ProjectVersion {
  id: number;
  name: string;
  description: string;
  status: VersionStatus;
  start_date: string | null;
  release_date: string | null;
  task_count: number;
  done_count: number;
  progress: number;
  created_at: string;
  updated_at: string;
}

/* ---------- Tasks (Jira-like Issues) ---------- */
export type TaskPriority = 'critical' | 'high' | 'medium' | 'low' | 'trivial';
export type TaskStatus = 'open' | 'in_progress' | 'in_review' | 'done' | 'closed';
export type TaskType = 'task' | 'bug' | 'story' | 'epic' | 'subtask';

export interface TaskComment {
  id: number;
  task: number;
  author: number | null;
  author_name: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface TaskAttachment {
  id: number;
  task: number;
  file: string;
  filename: string;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  created_at: string;
}

export interface Task {
  id: number;
  key: string;
  summary: string;
  description: string;
  task_type: TaskType;
  priority: TaskPriority;
  status: TaskStatus;
  reporter: number | null;
  reporter_name: string | null;
  assignee: number | null;
  assignee_name: string | null;
  department: number | null;
  department_name: string | null;
  version: number | null;
  version_name: string | null;
  parent: number | null;
  parent_key?: string | null;
  labels: Label[];
  label_ids?: number[];
  subtasks?: Task[];
  subtask_count?: number;
  comments?: TaskComment[];
  attachments?: TaskAttachment[];
  due_date: string | null;
  start_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

/* ---------- Task Stats (Reports) ---------- */
export interface TaskStats {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_type: Record<string, number>;
  by_department: Array<{ department__id: number; department__name: string; count: number }>;
  by_assignee: Array<{
    assignee__id: number;
    assignee__first_name: string;
    assignee__last_name: string;
    assignee__username: string;
    count: number;
  }>;
  created_per_day: Array<{ day: string; count: number }>;
  resolved_per_day: Array<{ day: string; count: number }>;
}
