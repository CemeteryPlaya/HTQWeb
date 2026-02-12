import { Header } from '@/components/Header';
import { useLanguageTransition } from '@/hooks/use-language-transition';
import { NewsSection } from '@/components/NewsSection';
import { Footer } from '@/components/Footer';

const News = () => {
  const isChanging = useLanguageTransition();

  return (
    <div className={`min-h-screen language-transition ${isChanging ? 'language-changing' : ''}`}>
      <Header />
      <main>
        <NewsSection />
      </main>
      <Footer />
    </div>
  );
};

export default News;
