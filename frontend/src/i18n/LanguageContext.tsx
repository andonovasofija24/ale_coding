import { useQueryClient } from '@tanstack/react-query'
import { formatDate as formatDateOnly } from '../lib/time'
import { createContext, useRef, useCallback, useContext, useEffect, useState, ReactNode } from 'react'
import { Lang, LANGS, LOCALES, TranslationKey, translations } from './translations'

export const LANG_STORAGE_KEY = 'ale_lang'
export const DEFAULT_LANG: Lang = 'mk'

/** Read the saved language; safe to call outside React (e.g. in the axios interceptor). */
export function getStoredLang(): Lang {
  try {
    const v = localStorage.getItem(LANG_STORAGE_KEY)
    if (v && (LANGS as string[]).includes(v)) return v as Lang
  } catch {
    /* storage unavailable */
  }
  return DEFAULT_LANG
}

type Params = Record<string, string | number>

interface LanguageContextType {
  lang: Lang
  setLang: (l: Lang) => void
  t: (key: TranslationKey, params?: Params) => string
  /** Translate a backend error `detail` if we know it, otherwise fall back. */
  tError: (detail: unknown, fallbackKey: TranslationKey) => string
  formatDate: (iso: string) => string
}

const LanguageContext = createContext<LanguageContextType | null>(null)

function interpolate(text: string, params?: Params) {
  if (!params) return text
  return text.replace(/\{(\w+)\}/g, (_, k) => (k in params ? String(params[k]) : `{${k}}`))
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(getStoredLang)

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  // Task titles and descriptions come from the server in the chosen language: reload what is on screen.
  const qc = useQueryClient()
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; return }
    qc.invalidateQueries()
  }, [lang, qc])

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem(LANG_STORAGE_KEY, l)
    } catch {
      /* storage unavailable */
    }
  }, [])

  const t = useCallback(
    (key: TranslationKey, params?: Params) => interpolate(translations[lang][key] ?? key, params),
    [lang]
  )

  const tError = useCallback(
    (detail: unknown, fallbackKey: TranslationKey) => {
      if (typeof detail === 'string') {
        const key = `err.${detail}` as TranslationKey
        return translations[lang][key] ?? detail
      }
      return t(fallbackKey)
    },
    [lang, t]
  )

  const formatDate = useCallback(
    (iso: string) => formatDateOnly(iso, lang),
    [lang]
  )

  return (
    <LanguageContext.Provider value={{ lang, setLang, t, tError, formatDate }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}
