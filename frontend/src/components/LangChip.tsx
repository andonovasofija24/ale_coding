import { langClass, langInfo } from '../lib/languages'

/** Language label drawn as a short highlighter swipe in that language's marker colour. */
export default function LangChip({ lang, size = 'sm' }: { lang: string; size?: 'sm' | 'md' }) {
  return (
    <span
      className={`${langClass(lang)} inline-flex items-center rounded font-bold text-ink bg-marker leading-none ${
        size === 'md' ? 'text-xs px-2 py-1' : 'text-[11px] px-1.5 py-[3px]'
      }`}
    >
      {langInfo(lang).label}
    </span>
  )
}
