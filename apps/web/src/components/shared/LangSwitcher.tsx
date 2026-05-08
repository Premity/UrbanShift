import { useTranslation } from 'react-i18next';
import Cookies from 'js-cookie';

export function LangSwitcher() {
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    Cookies.set('lang_pref', lng, { expires: 365, path: '/' });
  };

  return (
    <div className="flex items-center space-x-2 bg-card border border-border rounded-md px-2 py-1 shadow-sm">
      <select
        value={i18n.resolvedLanguage}
        onChange={(e) => changeLanguage(e.target.value)}
        className="bg-transparent text-foreground text-sm font-medium focus:outline-none cursor-pointer"
        aria-label="Select Language"
      >
        <option value="en">{t('language.en', 'English')}</option>
        <option value="hi">{t('language.hi', 'हिंदी')}</option>
        <option value="kn">{t('language.kn', 'ಕನ್ನಡ')}</option>
      </select>
    </div>
  );
}
