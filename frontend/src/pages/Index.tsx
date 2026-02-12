import { Header } from '@/components/Header';
import { useLanguageTransition } from '@/hooks/use-language-transition';
import { HeroSection } from '@/components/HeroSection';
import { ActivityDirections } from '@/components/ActivityDirections';
import { ProjectsSection } from '@/components/ProjectsSection';
import { ServicesSection } from '@/components/ServicesSection';
import { InvestCTA } from '@/components/InvestCTA';
import { StatsSection } from '@/components/StatsSection';
import { MissionSection } from '@/components/MissionSection';
import { AboutSection } from '@/components/AboutSection';
import { PartnersSection } from '@/components/PartnersSection';
import { NewsSection } from '@/components/NewsSection';
import { ContactSection } from '@/components/ContactSection';
import { Footer } from '@/components/Footer';

const Index = () => {
  const isChanging = useLanguageTransition();

  return (
    <div className={`min-h-screen language-transition ${isChanging ? 'language-changing' : ''}`}>
      <Header />
      <HeroSection />
      <ActivityDirections />
      <InvestCTA />
      <ProjectsSection />
      <ServicesSection />
      <StatsSection />
      <MissionSection />
      <AboutSection />
      <PartnersSection />
      <NewsSection />
      <ContactSection />
      <Footer />
    </div>
  );
};

export default Index;
