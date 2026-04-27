import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import api from '@/api/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/button';
import { Globe, Loader2, RotateCcw } from 'lucide-react';

type Lang = 'ru' | 'en' | 'kk';

/** Cycle order and button labels for each current language */
const LANG_CYCLE: Record<Lang, { next: Lang; icon: 'globe' | 'rotate'; label: string }> = {
  ru: { next: 'en', icon: 'globe', label: 'Read in English' },
  en: { next: 'kk', icon: 'globe', label: 'Оқу қазақша' },
  kk: { next: 'ru', icon: 'rotate', label: 'Читать на русском' },
};

interface TranslationCache {
  [lang: string]: { title: string; content: string };
}

const NewsDetail = () => {
  const { slug } = useParams();
  const [news, setNews] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [translations, setTranslations] = useState<TranslationCache>({});
  const [currentLang, setCurrentLang] = useState<Lang>('ru');

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    // Reset language state when article changes
    setCurrentLang('ru');
    setTranslations({});
    api
      .get(`cms/v1/news/by-slug/${encodeURIComponent(slug)}`)
      .then((res) => setNews(res.data))
      .catch((err) => setError(err?.response?.data?.detail || err.message))
      .finally(() => setLoading(false));
  }, [slug]);

  const handleToggleLanguage = async () => {
    if (!slug) return;

    const { next } = LANG_CYCLE[currentLang];

    // Switch back to Russian instantly (no request needed)
    if (next === 'ru') {
      setCurrentLang('ru');
      return;
    }

    // Use cached translation if already fetched
    if (translations[next]) {
      setCurrentLang(next);
      return;
    }

    // Fetch translation for the target language. Translation is async on the
    // backend (Dramatiq actor), so a 202 with a task_id can come back; treat
    // anything other than a populated translation payload as a soft failure.
    if (!news?.id) {
      toast.error('Невозможно перевести: статья не загружена');
      return;
    }
    setTranslating(true);
    try {
      const res = await api.post(`cms/v1/news/${news.id}/translate`, { target: next });
      const translated_title = (res.data as any)?.translated_title;
      const translated_content = (res.data as any)?.translated_content;
      if (translated_title && translated_content) {
        setTranslations((prev) => ({
          ...prev,
          [next]: { title: translated_title, content: translated_content },
        }));
        setCurrentLang(next);
      } else {
        toast('Перевод поставлен в очередь — попробуйте через минуту');
      }
    } catch (err: any) {
      console.error('Translation failed', err);
      toast.error(err?.response?.data?.detail || 'Ошибка перевода. Попробуйте позже.');
    } finally {
      setTranslating(false);
    }
  };

  const cached = currentLang !== 'ru' ? translations[currentLang] : null;
  const displayTitle = cached ? cached.title : news?.title;
  const displayContent = cached ? cached.content : (news?.content || news?.summary);

  const { icon, label } = LANG_CYCLE[currentLang];
  const ButtonIcon = icon === 'globe' ? Globe : RotateCcw;

  return (
    <div className="min-h-screen">
      <Header />
      <main className="section-padding container-custom">
        {loading && <p>Loading...</p>}
        {error && <p className="text-destructive">Error: {String(error)}</p>}
        {!loading && news && (
          <article className="max-w-3xl mx-auto bg-card rounded-2xl p-6 md:p-10 shadow-sm border mt-8">
            <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-4">
              <h1 className="font-display text-4xl font-bold">{displayTitle}</h1>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                onClick={handleToggleLanguage}
                disabled={translating}
              >
                {translating ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Translating...</>
                ) : (
                  <><ButtonIcon className="mr-2 h-4 w-4" />{label}</>
                )}
              </Button>
            </div>
            <div className="text-muted-foreground mb-6">
              {news.published_at ? new Date(news.published_at).toLocaleString() : 'Draft'}
            </div>
            {news.image && (
              <img src={news.image} alt={news.title} className="w-full rounded-lg mb-6 object-cover" />
            )}
            <div
              className="prose prose-slate max-w-none text-foreground"
              dangerouslySetInnerHTML={{ __html: displayContent }}
            />
          </article>
        )}
      </main>
      <Footer />
    </div>
  );
};

export default NewsDetail;
