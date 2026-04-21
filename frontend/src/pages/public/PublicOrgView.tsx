/**
 * Public org view — no auth required, accessed via shareable token.
 * Separate layout: no navigation, no sidebar, no header.
 * X-Robots-Tag: noindex is set by the backend endpoint.
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ReactFlowProvider } from '@xyflow/react';
import { OrgChart } from '@/components/hr/OrgChart';

interface OrgData {
  label: string | null;
  max_level: number;
  generated_at: string | null;
  tree: { nodes: any[]; edges: any[] };
}

type ViewState = 'loading' | 'error' | 'gone' | 'ok';

const ERROR_MESSAGES: Record<string, string> = {
  404: 'Ссылка не найдена или недействительна.',
  410: 'Эта ссылка уже была использована или истекла.',
};

const PublicOrgView = () => {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<ViewState>('loading');
  const [data, setData] = useState<OrgData | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [levelSlider, setLevelSlider] = useState(5);

  useEffect(() => {
    if (!token) { setState('error'); return; }

    // Determine API base from current origin (same domain, different path)
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api';

    fetch(`${apiBase}/hr/v1/public/org/${token}`, { method: 'GET' })
      .then(async (res) => {
        if (res.status === 404) { setErrorMsg(ERROR_MESSAGES[404]); setState('gone'); return; }
        if (res.status === 410) { setErrorMsg(ERROR_MESSAGES[410]); setState('gone'); return; }
        if (!res.ok) { setErrorMsg('Произошла ошибка. Обратитесь к отправителю ссылки.'); setState('error'); return; }
        const json: OrgData = await res.json();
        setData(json);
        setLevelSlider(json.max_level);
        setState('ok');
      })
      .catch(() => { setErrorMsg('Не удалось подключиться к серверу.'); setState('error'); });
  }, [token]);

  if (state === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-muted-foreground text-sm">Загрузка структуры…</div>
      </div>
    );
  }

  if (state === 'gone' || state === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-8">
        <div className="max-w-sm text-center space-y-3">
          <p className="text-4xl">🔒</p>
          <h1 className="text-lg font-semibold">Доступ недоступен</h1>
          <p className="text-sm text-muted-foreground">{errorMsg}</p>
        </div>
      </div>
    );
  }

  const maxAllowed = data!.max_level;

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Minimal header */}
      <header className="border-b bg-card px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-base">Структура организации</h1>
          {data?.label && <p className="text-xs text-muted-foreground mt-0.5">{data.label}</p>}
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground text-xs">Уровень детализации:</span>
            <input
              type="range"
              min={1}
              max={maxAllowed}
              value={levelSlider}
              onChange={(e) => setLevelSlider(parseInt(e.target.value))}
              className="w-28 h-1.5 accent-primary"
            />
            <span className="text-xs font-mono tabular-nums w-4">{levelSlider}</span>
          </div>
        </div>
      </header>

      {/* Graph */}
      <main className="flex-1 p-4">
        <ReactFlowProvider>
          <OrgChart
            rawNodes={data?.tree.nodes ?? []}
            rawEdges={data?.tree.edges ?? []}
            maxLevelFilter={levelSlider}
          />
        </ReactFlowProvider>
      </main>

      {/* Footer watermark */}
      <footer className="border-t bg-card px-6 py-2 flex items-center justify-between text-xs text-muted-foreground">
        <span>Просмотр ограничен. Контактные данные скрыты.</span>
        {data?.generated_at && (
          <span>Сгенерировано {new Date(data.generated_at).toLocaleString('ru')}</span>
        )}
      </footer>
    </div>
  );
};

export default PublicOrgView;
