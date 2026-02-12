import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';

const NewsDetail = () => {
  const { slug } = useParams();
  const [news, setNews] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    axios
      .get(`/api/news/${slug}/`)
      .then((res) => setNews(res.data))
      .catch((err) => setError(err?.response?.data || err.message))
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="section-padding container-custom">
        {loading && <p>Loading...</p>}
        {error && <p className="text-destructive">Error: {String(error)}</p>}
        {!loading && news && (
          <article className="max-w-3xl mx-auto">
            <h1 className="font-display text-4xl font-bold mb-4">{news.title}</h1>
            <div className="text-muted-foreground mb-6">
              {news.published_at ? new Date(news.published_at).toLocaleString() : 'Draft'}
            </div>
            {news.image && (
              <img src={news.image} alt={news.title} className="w-full rounded-lg mb-6 object-cover" />
            )}
            <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: news.content || news.summary }} />
          </article>
        )}
      </main>
      <Footer />
    </div>
  );
};

export default NewsDetail;
