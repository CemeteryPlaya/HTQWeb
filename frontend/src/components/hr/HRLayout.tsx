import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Users, Briefcase, FileText, Clock, ArrowLeft, Building2 } from 'lucide-react';

const navItems = [
  { to: '/manage/hr/employees', icon: Users, labelKey: 'hr.nav.employees' },
  { to: '/manage/hr/directory', icon: Building2, labelKey: 'hr.nav.directory' },
  { to: '/manage/hr/recruitment', icon: Briefcase, labelKey: 'hr.nav.recruitment' },
  { to: '/manage/hr/documents', icon: FileText, labelKey: 'hr.nav.documents' },
  { to: '/manage/hr/time-tracking', icon: Clock, labelKey: 'hr.nav.timeTracking' },
];

interface Props {
  children: React.ReactNode;
}

export const HRLayout: React.FC<Props> = ({ children }) => {
  const { t } = useTranslation();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        {/* Back to main page */}
        <Link
          to="/myprofile"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('hr.backToMain')}
        </Link>

        {/* Sub-navigation */}
        <nav className="flex items-center gap-1 mb-6 overflow-x-auto pb-2 border-b">
          {navItems.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                <item.icon className="h-4 w-4" />
                {t(item.labelKey)}
              </Link>
            );
          })}
        </nav>

        {children}
      </main>
      <Footer />
    </div>
  );
};

export default HRLayout;
