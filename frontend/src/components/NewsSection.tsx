import { useTranslation } from 'react-i18next';
import { ArrowRight, Calendar } from 'lucide-react';
import { Link } from 'react-router-dom';

const panels5 = '/images/panels5.webp';
const panels6 = '/images/panels6.webp';
const panels7 = '/images/panels7.webp';
import axios from 'axios';
import { useQuery } from '@tanstack/react-query';

export const NewsSection = () => {
  const { t } = useTranslation();

  const staticNews = [
    {
      title: t('news.items.solar_efficiency_title', { defaultValue: 'Solar Panel Efficiency Reaches New Heights with Latest Innovations' }),
      slug: 'solar-efficiency',
      date: 'January 2026',
      image: panels5,
      category: 'Technology',
    },
    {
      title: t('news.items.govt_investment_title', { defaultValue: 'Government Announces Major Investment in Solar Energy Projects' }),
      slug: 'government-investment-solar',
      date: 'January 2026',
      image: panels6,
      category: 'Industry',
    },
    {
      title: t('news.items.expansion_title', { defaultValue: 'Hi-Tech Group Expands Operations Across Central Asia' }),
      slug: 'expansion-central-asia',
      date: 'December 2025',
      image: panels7,
      category: 'Company',
    },
  ];

  const fetchNews = async () => {
    try {
      // Use relative URL - Vite proxy forwards /api to Django backend
      const res = await axios.get('/api/news/');
      return res.data;
    } catch (err) {
      // don't throw to avoid breaking the component; return null so fallback is used
      // console.warn('Failed to fetch news list', err);
      return null;
    }
  };

  interface APINewsItem {
    title: string;
    slug: string;
    published_at?: string;
    created_at?: string;
    image?: string;
    category?: string;
  }

  const { data: apiNews } = useQuery({
    queryKey: ['newsList'],
    queryFn: fetchNews,
    retry: false,
    staleTime: 1000 * 60 * 5,
  });

  const news = (apiNews && apiNews.length > 0)
    ? apiNews.map((n: APINewsItem) => ({
      title: n.title,
      slug: n.slug,
      date: n.published_at || n.created_at || '',
      image: n.image || panels5,
      category: n.category || '',
    }))
    : staticNews;

  return (
    <section id="news" className="section-padding bg-background">
      <div className="container-custom">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12">
          <div>
            <span className="text-secondary font-semibold text-sm uppercase tracking-wider">{t('news.tag')}</span>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-foreground mt-2">
              {t('news.title')}
            </h2>
          </div>
          <Link
            to="/news"
            className="inline-flex items-center gap-2 text-primary font-semibold hover:gap-4 transition-all group"
          >
            {t('news.view_all')}
            <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        {/* News Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {news.map((item, index) => (
            <article
              key={item.title}
              className="group bg-card rounded-2xl overflow-hidden shadow-soft card-hover"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {/* Image */}
              <div className="relative h-48 overflow-hidden">
                <img
                  src={item.image}
                  alt={item.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <div className="absolute top-4 left-4">
                  <span className="px-3 py-1 rounded-full bg-secondary text-secondary-foreground text-xs font-semibold">
                    {item.category}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="p-6">
                <div className="flex items-center gap-2 text-muted-foreground text-sm mb-3">
                  <Calendar size={14} />
                  <span>{item.date}</span>
                </div>
                <h3 className="font-display font-semibold text-lg text-foreground mb-4 line-clamp-2 group-hover:text-primary transition-colors">
                  {item.title}
                </h3>
                <Link
                  to={`/news/${item.slug}`}
                  className="inline-flex items-center gap-2 text-primary font-medium text-sm hover:gap-3 transition-all"
                >
                  {t('news.read_more')}
                  <ArrowRight size={14} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};
