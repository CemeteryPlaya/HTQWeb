import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react';
import directionLogo1 from '@/assets/directionsLogo1.png';
import directionLogo2 from '@/assets/directionsLogo2.png';
import directionLogo3 from '@/assets/directionsLogo3.png';
import directionLogo4 from '@/assets/directionsLogo4.png';
import directionLogo5 from '@/assets/directionsLogo5.png';

export const ActivityDirections = () => {
  const { t } = useTranslation();
  const [activeIndex, setActiveIndex] = useState(0);

  const directions = [
    {
      title: t('directions.items.earthworks.title'),
      image: directionLogo1,
      description: t('directions.items.earthworks.desc'),
    },
    {
      title: t('directions.items.construction.title'),
      image: directionLogo2,
      description: t('directions.items.construction.desc'),
    },
    {
      title: t('directions.items.installation.title'),
      image: directionLogo3,
      description: t('directions.items.installation.desc'),
    },
    {
      title: t('directions.items.sunpark.title'),
      image: directionLogo4,
      description: t('directions.items.sunpark.desc'),
    },
    {
      title: t('directions.items.substation.title'),
      image: directionLogo5,
      description: t('directions.items.substation.desc'),
    },
  ];

  const nextSlide = () => {
    setActiveIndex((prev) => (prev + 1) % directions.length);
  };

  const prevSlide = () => {
    setActiveIndex((prev) => (prev - 1 + directions.length) % directions.length);
  };

  return (
    <section className="section-padding bg-card">
      <div className="container-custom">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <span className="text-secondary font-semibold text-sm uppercase tracking-wider">{t('directions.tag')}</span>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-foreground mt-2">
              {t('directions.title')}
            </h2>
          </div>
          <div className="flex gap-3">
            <button
              onClick={prevSlide}
              className="w-12 h-12 rounded-full border-2 border-primary/30 flex items-center justify-center hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={nextSlide}
              className="w-12 h-12 rounded-full border-2 border-primary/30 flex items-center justify-center hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>

        {/* Cards Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {directions.map((direction, index) => (
            <div
              key={direction.title}
              className={`group relative rounded-2xl overflow-hidden card-hover cursor-pointer ${index === activeIndex ? 'ring-2 ring-secondary' : ''
                }`}
              onClick={() => setActiveIndex(index)}
            >
              <div className="aspect-[4/3] relative">
                <img
                  src={direction.image}
                  alt={direction.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/90 via-primary/40 to-transparent" />
              </div>
              <div className="absolute bottom-0 left-0 right-0 p-6">
                <h3 className="font-display text-xl font-bold text-primary-foreground mb-2 transition-transform duration-300 group-hover:-translate-y-2">
                  {direction.title}
                </h3>
                <div className="grid grid-rows-[0fr] group-hover:grid-rows-[1fr] transition-all duration-300">
                  <div className="min-h-0 overflow-hidden">
                    <p className="text-primary-foreground/70 text-sm line-clamp-2">
                      {direction.description}
                    </p>
                    <div className="flex items-center gap-2 text-secondary mt-2">
                      <span className="text-sm font-medium">{t('directions.more')}</span>
                      <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
