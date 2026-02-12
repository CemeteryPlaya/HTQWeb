import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';
import { LanguageSwitcher } from './LanguageSwitcher';
import logo from '@/assets/logo.png';

export const Header = () => {
  const { t } = useTranslation();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const offset = window.scrollY;
      if (offset > 50) {
        setIsScrolled(true);
      } else if (offset < 30) {
        setIsScrolled(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: t('header.about'), href: '#about' },
    { label: t('header.projects'), href: '/projects' },
    { label: t('header.services'), href: '/services' },
    { label: t('header.news'), href: '/news' },
  ];

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-500 ${isScrolled
        ? 'py-3 bg-white/85 shadow-sm border-b border-white/40 opacity-95'
        : 'py-5 bg-white/70 shadow-sm border-b border-white/30 opacity-90'
        }`}
    >
      <div className="container-custom flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-3 group">
          <img
            src={logo}
            alt="Hi-Tech Group Logo"
            className="h-10 w-auto transition-transform duration-300 group-hover:scale-110"
          />
          <div className={`flex flex-col justify-center h-10 transition-colors duration-300 text-foreground`}>
            <span className="font-display font-bold text-lg leading-tight">Hi-Tech Group</span>
            <span className="text-[10px] align-center leading-tight opacity-80 max-w-[140px]">Construction services in energy sector</span>
          </div>
        </a>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="link-underline font-medium transition-colors duration-300 text-foreground hover:text-primary"
            >
              {link.label}
            </a>
          ))}
          {/* Simple check: if we can access /v1/admin/users/ (handled by error in page), 
              but better to filter via profile roles if available. 
              For now just a link, protected by page level. 
              Or we can fetch profile here.
          */}
          <LanguageSwitcher />
        </nav>

        {/* CTA Button */}
        <div className="hidden md:block">
          <Link to="/contacts">
            <Button
              className={`px-6 py-2.5 rounded-full font-medium transition-all duration-300 ${isScrolled
                ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                : 'bg-secondary text-secondary-foreground hover:bg-secondary/90'
                }`}
            >
              {t('header.contacts')}
            </Button>
          </Link>
        </div>

        {/* Mobile Menu Toggle */}
        <button
          className="md:hidden p-2 transition-colors text-foreground"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 glass shadow-elevated animate-fade-in">
          <nav className="container-custom py-6 flex flex-col gap-4">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-foreground font-medium py-2 hover:text-primary transition-colors"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <div className="flex gap-4 items-center">
              <LanguageSwitcher />
            </div>
            <Link to="/contacts" onClick={() => setIsMobileMenuOpen(false)}>
              <Button className="btn-primary mt-4 w-full">
                {t('header.contacts')}
              </Button>
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
};
