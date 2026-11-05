import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, Loader2, Megaphone } from 'lucide-react'
import { mailApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { Announcement } from '../../types'
import { formatDateTime } from '../../lib/time'

/** What the teachers sent to the students of the course (the same text as the e-mail, in the student's language). */
export default function Announcements({ courseId, limit }: { courseId: string; limit?: number }) {
  const { t, lang } = useLanguage()
  const { data = [], isLoading } = useQuery<Announcement[]>({
    queryKey: ['announcements', courseId], queryFn: () => mailApi.announcements(courseId),
  })
  const [open, setOpen] = useState<string | null>(null)
  if (isLoading) return <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>
  const items = limit ? data.slice(0, limit) : data
  if (items.length === 0) {
    return limit ? null : (
      <div className="card px-6 py-12 text-center text-ink-muted"><Megaphone className="mx-auto mb-2 text-ink-faint" /> {t('notices.empty')}</div>
    )
  }
  return (
    <ul className="card divide-y divide-line-soft overflow-hidden">
      {items.map((a) => {
        const expanded = open === a.id || (!limit && items.length === 1)
        return (
          <li key={a.id}>
            <button onClick={() => setOpen(expanded ? null : a.id)} aria-expanded={expanded}
              className="w-full text-left px-4 sm:px-5 py-3 flex items-start gap-3 hover:bg-paper/60">
              <span className="w-8 h-8 rounded-full bg-cobalt-soft text-cobalt inline-flex items-center justify-center shrink-0"><Megaphone size={15} /></span>
              <span className="flex-1 min-w-0">
                <span className="block font-semibold break-words">{a.subject}</span>
                <span className="block text-[12px] text-ink-muted">{formatDateTime(a.sent_at, lang)}</span>
              </span>
              <ChevronDown size={16} className={`mt-1 text-ink-faint transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
            {expanded && (
              <div className="px-4 sm:px-5 pb-4 pl-[3.75rem] sm:pl-[4.25rem]">
                <pre className="whitespace-pre-wrap break-words font-sans text-sm text-ink-soft">{a.body}</pre>
                {a.assignment_id && <Link to={`/assignments/${a.assignment_id}`} className="mt-2 inline-block text-sm font-semibold text-cobalt hover:underline">{t('notices.open')}</Link>}
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
