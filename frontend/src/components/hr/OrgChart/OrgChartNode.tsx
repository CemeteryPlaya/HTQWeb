import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';

export type OrgNodeData = {
  label: string;
  type: 'department' | 'position' | 'employee';
  unit_type?: string | null;
  level?: number | null;
  weight?: number | null;
  meta?: Record<string, unknown>;
};

const LEVEL_BORDER: Record<number, string> = {
  1: 'border-purple-500',
  2: 'border-blue-500',
  3: 'border-green-500',
  4: 'border-yellow-500',
  5: 'border-gray-400',
};

const TYPE_BG: Record<string, string> = {
  department: 'bg-slate-50 dark:bg-slate-900',
  headquarters: 'bg-purple-50 dark:bg-purple-950',
  division: 'bg-blue-50 dark:bg-blue-950',
  position: 'bg-white dark:bg-neutral-900',
  employee: 'bg-emerald-50 dark:bg-emerald-950',
};

const TYPE_ICON: Record<string, string> = {
  headquarters: '🏛',
  division: '🏢',
  department: '🗂',
  position: '💼',
  employee: '👤',
};

function getLevelBorder(level: number | null | undefined): string {
  if (!level) return 'border-gray-300';
  return LEVEL_BORDER[level] ?? LEVEL_BORDER[5];
}

function getBg(type: string, unit_type?: string | null): string {
  if (type === 'department' && unit_type) return TYPE_BG[unit_type] ?? TYPE_BG.department;
  return TYPE_BG[type] ?? TYPE_BG.position;
}

function getIcon(type: string, unit_type?: string | null): string {
  if (type === 'department' && unit_type) return TYPE_ICON[unit_type] ?? TYPE_ICON.department;
  return TYPE_ICON[type] ?? '•';
}

export const OrgChartNode = memo(({ data }: NodeProps) => {
  const d = data as OrgNodeData;
  const borderCls = getLevelBorder(d.level);
  const bgCls = getBg(d.type, d.unit_type);

  return (
    <div
      className={`
        relative min-w-[160px] max-w-[220px] rounded-xl border-2 px-3 py-2 shadow-sm
        text-sm select-none cursor-default
        ${borderCls} ${bgCls}
      `}
    >
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground/40" />

      <div className="flex items-start gap-2">
        <span className="text-base leading-none mt-0.5">{getIcon(d.type, d.unit_type)}</span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold leading-tight truncate text-foreground">{d.label}</p>
          {d.meta?.position_title && (
            <p className="text-xs text-muted-foreground truncate">{String(d.meta.position_title)}</p>
          )}
          {d.meta?.department && (
            <p className="text-xs text-muted-foreground truncate">{String(d.meta.department)}</p>
          )}
        </div>
      </div>

      {(d.level != null || d.weight != null) && (
        <div className="flex gap-1 mt-1.5 flex-wrap">
          {d.level != null && (
            <span className="inline-flex items-center rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              L{d.level}
            </span>
          )}
          {d.weight != null && (
            <span className="inline-flex items-center rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
              w{d.weight}
            </span>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground/40" />
    </div>
  );
});

OrgChartNode.displayName = 'OrgChartNode';
