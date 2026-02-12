import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/button';

const AdminAbout = () => {
  const [message, setMessage] = useState<string | null>(null);
  const { t } = useTranslation();

  const handlePlaceholder = () => {
    setMessage(t('profile.about.placeholderMessage'));
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">{t('profile.about.title')}</h1>
        <div className="bg-card rounded-lg border p-6">
          <p className="mb-4">{t('profile.about.description')}</p>
          <Button onClick={handlePlaceholder}>{t('profile.about.checkConnection')}</Button>
          {message && <div className="mt-4 text-sm text-muted-foreground">{message}</div>}
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default AdminAbout;
