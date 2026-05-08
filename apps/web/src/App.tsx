import React from 'react';
import { Header } from './components/shared/Header';
import { useTranslation } from 'react-i18next';

function App() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col bg-background font-sans text-foreground">
      <Header />
      <main className="flex-1 flex items-center justify-center container py-12">
        <div className="text-center max-w-2xl">
          <h1 className="text-5xl font-extrabold tracking-tight lg:text-6xl text-primary mb-6">
            {t('landing.title', 'UrbanShift')}
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            {t('landing.subtitle', 'AI-powered urban migrant assistance platform')}
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <button className="bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-8 rounded-md font-medium transition-colors">
              {t('landing.getStarted', 'Get Started')}
            </button>
          </div>
          
          <div className="mt-12 flex justify-center gap-2 flex-wrap">
            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
              {t('landing.seekerType.job', 'Jobs')}
            </span>
            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
              {t('landing.seekerType.housing', 'Housing')}
            </span>
            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
              {t('landing.seekerType.both', 'Both')}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
