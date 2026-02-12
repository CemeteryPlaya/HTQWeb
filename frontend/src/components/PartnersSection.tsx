import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import risenLogo from '@/assets/risenLogo.svg';
import sepcoLogo from '@/assets/sepcoLogo.svg';
import tbeaLogo from '@/assets/tbeaLogo.svg';
import huaweiLogo from '@/assets/huaweiLogo.svg';
import trinaSolarLogo from '@/assets/trinaSolarLogo.svg';
import unitedGreenLogo from '@/assets/unitedGreenLogo.svg';
import carerLogo from '@/assets/carerLogo.svg';

const partners = [
  { name: 'Risen', logo: risenLogo },
  { name: 'United Green', logo: unitedGreenLogo },
  { name: 'Huawei', logo: huaweiLogo },
  { name: 'Trina Solar', logo: trinaSolarLogo },
  { name: 'Carer', logo: carerLogo },
  { name: 'TBEA', logo: tbeaLogo },
  { name: 'SEPCO', logo: sepcoLogo },
];

export const PartnersSection = () => {
  const { t } = useTranslation();
  const trackRef = useRef<HTMLDivElement>(null);
  const posRef = useRef(0);
  const pausedRef = useRef(false);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;

    const animate = () => {
      if (!pausedRef.current && el) {
        const halfWidth = el.scrollWidth / 2;
        posRef.current -= 0.4;
        if (posRef.current <= -halfWidth) {
          posRef.current = 0;
        }
        el.style.transform = `translateX(${posRef.current}px)`;
      }
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return (
    <section className="py-16 bg-background border-y border-border">
      <div className="container-custom">
        <div className="text-center mb-12">
          <span className="text-secondary font-semibold text-sm uppercase tracking-wider">{t('partners.tag')}</span>
          <h3 className="font-display text-2xl md:text-3xl font-bold text-foreground mt-2">
            {t('partners.title')}
          </h3>
        </div>

        {/* Infinite scroll logos */}
        <div
          className="relative overflow-hidden"
          onMouseEnter={() => { pausedRef.current = true; }}
          onMouseLeave={() => { pausedRef.current = false; }}
        >
          <div ref={trackRef} className="flex">
            {[...partners, ...partners].map((partner, index) => (
              <div
                key={`${partner.name}-${index}`}
                className="flex-shrink-0 mx-8 lg:mx-12 grayscale hover:grayscale-0 opacity-60 hover:opacity-100 transition-all duration-300"
              >
                <img
                  src={partner.logo}
                  alt={partner.name}
                  className="h-12 lg:h-16 w-auto object-contain"
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
