/**
 * OrgChart — interactive company org-chart using React Flow + dagre layout.
 * Supports positions / employees / both modes; PNG/SVG export; level filter.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng, toSvg } from 'html-to-image';

import { OrgChartNode } from './OrgChartNode';
import { applyDagreLayout } from './useOrgLayout';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const nodeTypes = { orgNode: OrgChartNode };

type RawNode = {
  id: string;
  label: string;
  type: string;
  unit_type?: string | null;
  level?: number | null;
  weight?: number | null;
  meta?: Record<string, unknown>;
};

type RawEdge = {
  source: string;
  target: string;
  relation_type: string;
};

type Mode = 'positions' | 'employees' | 'both';
type Direction = 'TB' | 'LR';

interface OrgChartProps {
  rawNodes: RawNode[];
  rawEdges: RawEdge[];
  maxLevelFilter?: number;    // show nodes up to this level only (for public view)
  isLoading?: boolean;
}

const EDGE_STYLE: Record<string, { stroke: string; strokeDasharray?: string }> = {
  direct: { stroke: '#64748b' },
  functional: { stroke: '#3b82f6', strokeDasharray: '6 3' },
  project: { stroke: '#f59e0b', strokeDasharray: '3 3' },
  structural: { stroke: '#94a3b8' },
  membership: { stroke: '#cbd5e1', strokeDasharray: '4 2' },
  employment: { stroke: '#86efac' },
};

function buildFlowElements(
  rawNodes: RawNode[],
  rawEdges: RawEdge[],
  levelFilter: number | null,
  direction: Direction,
): { nodes: Node[]; edges: Edge[] } {
  const visibleIds = new Set(
    rawNodes
      .filter((n) => levelFilter == null || (n.level == null || n.level <= levelFilter))
      .map((n) => n.id),
  );

  const nodes: Node[] = rawNodes
    .filter((n) => visibleIds.has(n.id))
    .map((n) => ({
      id: n.id,
      type: 'orgNode',
      position: { x: 0, y: 0 },
      data: {
        label: n.label,
        type: n.type,
        unit_type: n.unit_type,
        level: n.level,
        weight: n.weight,
        meta: n.meta,
      },
    }));

  const edges: Edge[] = rawEdges
    .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
    .map((e) => ({
      id: `${e.source}->${e.target}-${e.relation_type}`,
      source: e.source,
      target: e.target,
      style: EDGE_STYLE[e.relation_type] ?? EDGE_STYLE.structural,
      animated: e.relation_type === 'direct',
    }));

  return applyDagreLayout(nodes, edges, direction);
}

export function OrgChart({ rawNodes, rawEdges, maxLevelFilter, isLoading }: OrgChartProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [levelFilter, setLevelFilter] = useState<number | null>(maxLevelFilter ?? null);
  const [direction, setDirection] = useState<Direction>('TB');
  const { fitView } = useReactFlow();
  const containerRef = useRef<HTMLDivElement>(null);

  const maxLevel = Math.max(
    1,
    ...rawNodes.map((n) => n.level ?? 0),
  );

  useEffect(() => {
    const { nodes: n, edges: e } = buildFlowElements(rawNodes, rawEdges, levelFilter, direction);
    setNodes(n);
    setEdges(e);
    // fit after layout settles
    setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50);
  }, [rawNodes, rawEdges, levelFilter, direction, fitView]);

  const exportPng = useCallback(async () => {
    if (!containerRef.current) return;
    const dataUrl = await toPng(containerRef.current, { backgroundColor: '#ffffff' });
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = 'org-chart.png';
    a.click();
  }, []);

  const exportSvg = useCallback(async () => {
    if (!containerRef.current) return;
    const dataUrl = await toSvg(containerRef.current, { backgroundColor: '#ffffff' });
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = 'org-chart.svg';
    a.click();
  }, []);

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Control panel */}
      <div className="flex flex-wrap items-center gap-2 px-1">
        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Глубина:</span>
          <Select
            value={levelFilter == null ? 'all' : String(levelFilter)}
            onValueChange={(v) => setLevelFilter(v === 'all' ? null : parseInt(v))}
          >
            <SelectTrigger className="h-8 w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все</SelectItem>
              {Array.from({ length: maxLevel }, (_, i) => i + 1).map((l) => (
                <SelectItem key={l} value={String(l)}>до L{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Направление:</span>
          <Select value={direction} onValueChange={(v) => setDirection(v as Direction)}>
            <SelectTrigger className="h-8 w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="TB">Сверху вниз</SelectItem>
              <SelectItem value="LR">Слева направо</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button size="sm" variant="outline" onClick={() => fitView({ padding: 0.15, duration: 300 })}>
          По экрану
        </Button>
        <Button size="sm" variant="outline" onClick={exportPng}>PNG</Button>
        <Button size="sm" variant="outline" onClick={exportSvg}>SVG</Button>

        {/* Legend */}
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block w-6 h-0.5 bg-slate-500" /> прямое
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-6 h-0.5 border-t-2 border-dashed border-blue-400" /> функциональное
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-6 h-0.5 border-t-2 border-dotted border-amber-400" /> проектное
          </span>
        </div>
      </div>

      {/* Graph canvas */}
      <div ref={containerRef} className="flex-1 rounded-xl border bg-background min-h-[500px]">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
            Загрузка структуры…
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.1}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
          >
            <Controls />
            <MiniMap zoomable pannable />
            <Background gap={16} size={1} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
