import { CalendarClock } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { Assignment, AssignmentKind, AssignmentStatus } from '../../types'
import { countdown, formatDateTime, relative, useNow } from '../../lib/time'

const STATUS_TONE: Record<AssignmentStatus, string> = {
  draft: 'bg-line-soft text-ink-soft',
  scheduled: 'bg-cobalt-soft text-cobalt',
  open: 'bg-ok-soft text-ok',
  late: 'bg-bad-soft text-bad',
  closed: 'bg-paper text-ink-muted border border-line',
}

export function StatusBadge({ status }: { status: AssignmentStatus }) {
  const { t } = useLanguage()
  return (
    <span className={`inline-flex items-center text-[11px] font-semibold rounded-full px-2 py-0.5 whitespace-nowrap ${STATUS_TONE[status]}`}>
      {t(`astatus.${status}` as any)}
    </span>
  )
}

export function KindBadge({ kind }: { kind: AssignmentKind }) {
  const { t } = useLanguage()
  return (
    <span className="inline-flex items-center text-[11px] font-bold uppercase tracking-wide text-ink-muted">
      {t(`akind.${kind}` as any)}
    </span>
  )
}

/** "Рок: пет, 24 окт., 23:59 · за 2 дена" — with a live countdown in the last 24 hours. */
export function Deadline({ a, live = false }: { a: Pick<Assignment, 'due_at' | 'opens_at' | 'status'>; live?: boolean }) {
  const { t, lang } = useLanguage()
  const now = useNow(live ? 1000 : 60_000)
  if (a.status === 'scheduled' && a.opens_at) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[13px] text-ink-muted">
        <CalendarClock size={14} /> {t('assign.opens', { when: formatDateTime(a.opens_at, lang) })}
      </span>
    )
  }
  if (!a.due_at) return <span className="text-[13px] text-ink-muted">{t('assign.noDeadline')}</span>
  const left = countdown(a.due_at, now)
  const soon = left && new Date(a.due_at).getTime() - now < 24 * 3600_000
  return (
    <span className={`inline-flex flex-wrap items-center gap-x-1.5 text-[13px] ${soon ? 'text-bad font-semibold' : 'text-ink-muted'}`}>
      <CalendarClock size={14} />
      {t('assign.due', { when: formatDateTime(a.due_at, lang) })}
      <span className="tabular-nums">· {left ? (soon ? left : relative(a.due_at, lang, now)) : t('assign.passed')}</span>
    </span>
  )
}

/** "7 / 10" with the score in green when full marks. */
export function Points({ got, max }: { got?: number | null; max: number }) {
  const full = got != null && got >= max && max > 0
  return (
    <span className="tabular-nums text-sm">
      <span className={`font-bold ${got == null ? 'text-ink-faint' : full ? 'text-ok' : 'text-ink'}`}>{got == null ? '—' : fmt(got)}</span>
      <span className="text-ink-muted"> / {fmt(max)}</span>
    </span>
  )
}

export const fmt = (n: number) => (Math.round(n * 100) / 100).toString()
