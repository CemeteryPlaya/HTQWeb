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
  effective_release_date?: string | null;
  task_count: number;
  done_count: number;
  progress: number;
  created_at: string;
  updated_at: string;
}

/* ---------- Tasks ---------- */
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

export interface TaskActivity {
  id: number;
  task: number;
  actor: number | null;
  actor_name: string | null;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export type TaskLinkType = 'blocks' | 'is_blocked_by' | 'relates_to' | 'duplicates';

export interface TaskLink {
  id: number;
  source: number;
  target: number;
  link_type: TaskLinkType;
  source_key: string;
  source_summary: string;
  target_key: string;
  target_summary: string;
  created_by: number | null;
  created_at: string;
}

export interface Notification {
  id: number;
  recipient: number;
  actor: number | null;
  actor_name: string | null;
  verb: string;
  task: number | null;
  task_key: string | null;
  is_read: boolean;
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
  reporter: number;
  reporter_name?: string;
  assignee: number | null;
  assignee_name?: string;
  department: number | null;
  department_name?: string;
  version: number | null;
  version_name?: string;
  parent: number | null;
  parent_key?: string;
  labels: Label[];
  label_ids?: number[];
  due_date: string | null;
  start_date: string | null;
  effective_start_date?: string | null;
  effective_due_date?: string | null;
  date_warnings?: Array<{ code: string; message: string }>;
  completed_at: string | null;

  comments?: TaskComment[];
  attachments?: TaskAttachment[];
  subtasks?: Partial<Task>[];
  activities?: TaskActivity[];
  outgoing_links?: TaskLink[];
  incoming_links?: TaskLink[];

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
