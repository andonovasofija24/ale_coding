import { ClipboardCheck, FileText, FolderArchive } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import LangChip from './LangChip'

const ICON = { document: <FileText size={11} />, project: <FolderArchive size={11} />, offline: <ClipboardCheck size={11} /> } as const

/** The programming language of a code task, or the kind of work (document / project / on site) of any other task. */
export default function TaskChip({ kind, lang }: { kind?: string; lang: string }) {
  const { t } = useLanguage()
  if (!kind || kind === 'code') return <LangChip lang={lang} />
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-ink-soft bg-paper border border-line rounded px-1.5 py-px whitespace-nowrap">
      {ICON[kind as keyof typeof ICON]} {t(`kind.${kind}` as any)}
    </span>
  )
}
