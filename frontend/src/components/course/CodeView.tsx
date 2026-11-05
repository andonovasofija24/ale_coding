import { useState } from 'react'
import { MessageSquarePlus, Trash2, X } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { LineComment } from '../../types'

/**
 * Read-only code with line numbers.
 * - `highlight`: line ranges to mark (matched parts in the similarity view)
 * - `comments`: teacher comments shown under their line
 * - `onAdd` / `onDelete`: staff can comment on a line (click the line number)
 */
export default function CodeView({ code, highlight = [], comments = [], onAdd, onDelete, maxHeight = '32rem' }: {
  code: string
  highlight?: [number, number][]
  comments?: LineComment[]
  onAdd?: (line: number, body: string) => Promise<void>
  onDelete?: (id: string) => Promise<void>
  maxHeight?: string
}) {
  const { t } = useLanguage()
  const lines = code.replace(/\n$/, '').split('\n')
  const [open, setOpen] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const marked = (n: number) => highlight.some(([a, b]) => n >= a && n <= b)
  const byLine = new Map<number, LineComment[]>()
  comments.forEach((c) => byLine.set(c.line, [...(byLine.get(c.line) ?? []), c]))

  const save = async () => {
    if (!onAdd || open == null || !draft.trim()) return
    setSaving(true)
    try { await onAdd(open, draft.trim()); setDraft(''); setOpen(null) } finally { setSaving(false) }
  }

  return (
    <div className="rounded-lg border border-line bg-surface overflow-auto font-mono text-[12.5px] leading-[1.6]" style={{ maxHeight }}>
      <table className="w-full border-collapse">
        <tbody>
          {lines.map((ln, i) => {
            const n = i + 1
            const notes = byLine.get(n) ?? []
            return (
              <FragmentRow key={n}>
                <tr className={marked(n) ? 'bg-marker-soft' : notes.length ? 'bg-cobalt-soft/50' : ''}>
                  <td className={`select-none text-right align-top pl-2 pr-2 w-10 text-ink-faint border-r ${marked(n) ? 'border-marker' : 'border-line-soft'}`}>
                    {onAdd ? (
                      <button type="button" onClick={() => { setOpen(open === n ? null : n); setDraft('') }}
                        className="group w-full text-right hover:text-cobalt" title={t('review.commentLine', { n })} aria-label={t('review.commentLine', { n })}>
                        <span className="group-hover:hidden">{n}</span>
                        <MessageSquarePlus size={13} className="hidden group-hover:inline -mt-0.5" />
                      </button>
                    ) : n}
                  </td>
                  <td className="pl-3 pr-4 whitespace-pre text-ink">{ln || ' '}</td>
                </tr>
                {notes.map((c, j) => (
                  <tr key={c.id ?? `${n}-${j}`}>
                    <td className="border-r border-line-soft" />
                    <td className="px-3 py-1.5">
                      <div className="font-sans text-[13px] leading-snug rounded-md border border-cobalt/25 bg-cobalt-soft px-3 py-2 text-ink flex gap-2 max-w-[44rem]">
                        <p className="flex-1 whitespace-pre-wrap">
                          {c.author && <span className="font-semibold text-cobalt">{c.author}: </span>}{c.body}
                        </p>
                        {onDelete && c.id && (
                          <button type="button" onClick={() => onDelete(c.id!)} className="text-ink-faint hover:text-bad shrink-0" aria-label={t('review.deleteComment')}>
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {open === n && (
                  <tr>
                    <td className="border-r border-line-soft" />
                    <td className="px-3 py-2">
                      <div className="font-sans max-w-[44rem] rounded-md border border-line bg-paper p-2">
                        <textarea autoFocus rows={2} className="input h-auto py-1.5 text-[13px]" value={draft} onChange={(e) => setDraft(e.target.value)}
                          placeholder={t('review.commentPlaceholder', { n })}
                          onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save() }} />
                        <div className="mt-1.5 flex items-center gap-2">
                          <button type="button" onClick={save} disabled={saving || !draft.trim()} className="btn-primary btn-sm">{t('review.addComment')}</button>
                          <button type="button" onClick={() => setOpen(null)} className="btn-ghost btn-sm px-2" aria-label={t('form.cancel')}><X size={14} /></button>
                          <span className="ml-auto text-[11px] text-ink-muted">Ctrl+Enter</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </FragmentRow>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function FragmentRow({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
