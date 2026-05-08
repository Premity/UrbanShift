import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from '../locales/en.json';
import hi from '../locales/hi.json';
import kn from '../locales/kn.json';

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  kn: { translation: kn }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'hi', 'kn'],
    detection: {
      order: ['cookie', 'navigator'],
      lookupCookie: 'lang_pref',
      caches: ['cookie'],
      cookieMinutes: 60 * 24 * 365, // 1 year
      cookieOptions: { path: '/' }
    },
    interpolation: {
      escapeValue: false // react already safes from xss
    }
  });

export default i18n;
