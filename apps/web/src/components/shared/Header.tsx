import { Link } from 'react-router-dom';
import { LangSwitcher } from './LangSwitcher';
import { useTranslation } from 'react-i18next';
import { Building2 } from 'lucide-react';

export function Header() {
  const { t } = useTranslation();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between">
        <Link to="/" className="flex items-center space-x-2 hover:opacity-95 transition-opacity cursor-pointer">
          <Building2 className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg text-primary">{t('header.title', 'UrbanShift')}</span>
        </Link>
        <div className="flex items-center space-x-4">
          <LangSwitcher />
        </div>
      </div>
    </header>
  );
}
