import { useLanguage } from '../i18n/LanguageContext'
import { LANGS } from '../i18n/translations'

/** Compact МК / EN segmented toggle. */
export default function LanguageSwitcher({ className = '', onDark = false }: { className?: string; onDark?: boolean }) {
  const { lang, setLang } = useLanguage()

  return (
    <div
      role="group"
      aria-label="Јазик / Language"
      className={`inline-flex rounded-lg p-0.5 text-xs font-bold ${
        onDark ? 'bg-white/10' : 'bg-paper border border-line'
      } ${className}`}
    >
      {LANGS.map((l) => {
        const active = lang === l
        return (
          <button
            key={l}
            type="button"
            onClick={() => setLang(l)}
            aria-pressed={active}
            className={`h-7 px-2.5 rounded-md transition-colors ${
              active
                ? onDark
                  ? 'bg-white text-ink'
                  : 'bg-surface text-ink shadow-[0_1px_2px_rgba(26,34,51,.12)]'
                : onDark
                  ? 'text-white/60 hover:text-white'
                  : 'text-ink-muted hover:text-ink'
            }`}
          >
            {l === 'mk' ? 'МК' : 'EN'}
          </button>
        )
      })}
    </div>
  )
}
