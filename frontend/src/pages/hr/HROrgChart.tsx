import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ReactFlowProvider } from '@xyflow/react';
import api from '@/api/client';
import HRLayout from '@/components/hr/HRLayout';
import { OrgChart } from '@/components/hr/OrgChart';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useQuery as useDeptQuery } from '@tanstack/react-query';

type Mode = 'positions' | 'employees' | 'both';

interface Department { id: number; name: string }

const HROrgChart = () => {
  const [mode, setMode] = useState<Mode>('positions');
  const [rootId, setRootId] = useState<string>('all');
  const [depth, setDepth] = useState(5);

  const { data: departments } = useDeptQuery({
    queryKey: ['hr-departments'],
    queryFn: async () => {
      const res = await api.get<Department[]>('hr/departments/');
      return Array.isArray(res.data) ? res.data : (res.data as any).results ?? [];
    },
  });

  const { data: treeData, isLoading, error } = useQuery({
    queryKey: ['org-tree', mode, rootId, depth],
    queryFn: async () => {
      const params = new URLSearchParams({ mode, depth: String(depth) });
      if (rootId !== 'all') params.append('root_id', rootId);
      const res = await api.get(`hr/v1/org/tree?${params}`);
      return res.data as { nodes: any[]; edges: any[] };
    },
  });

  return (
    <HRLayout
      title="Структура компании"
      subtitle="Интерактивное дерево должностей и сотрудников"
    >
      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Отдел:</span>
          <Select value={rootId} onValueChange={setRootId}>
            <SelectTrigger className="h-8 w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Вся компания</SelectItem>
              {departments?.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Показать:</span>
          <Select value={mode} onValueChange={(v) => setMode(v as Mode)}>
            <SelectTrigger className="h-8 w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="positions">Должности</SelectItem>
              <SelectItem value="employees">Сотрудники</SelectItem>
              <SelectItem value="both">Оба варианта</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Уровней:</span>
          <Select value={String(depth)} onValueChange={(v) => setDepth(parseInt(v))}>
            <SelectTrigger className="h-8 w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[2, 3, 4, 5, 7, 10].map((d) => (
                <SelectItem key={d} value={String(d)}>{d}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 mb-4">
          Не удалось загрузить структуру
        </div>
      )}

      <div className="h-[calc(100vh-280px)] min-h-[500px]">
        <ReactFlowProvider>
          <OrgChart
            rawNodes={treeData?.nodes ?? []}
            rawEdges={treeData?.edges ?? []}
            isLoading={isLoading}
          />
        </ReactFlowProvider>
      </div>
    </HRLayout>
  );
};

export default HROrgChart;
