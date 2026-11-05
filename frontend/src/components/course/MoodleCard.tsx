import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, School, Send, Unlink, Users } from 'lucide-react'
import { ltiApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { relative } from '../../lib/time'
import { IconTile } from '../EmptyState'

interface Ctx {
  id: string; platform: string; issuer: string; label: string; title: string; roster: boolean; grades: boolean
  last_roster_sync: string | null; last_grade_sync: string | null
}

/** Course staff: the Moodle (courses.finki) course this course is linked to — participants in, points out. */
export default function MoodleCard({ courseId, teacher, hideWhenUnlinked = false }: { courseId: string; teacher: boolean; hideWhenUnlinked?: boolean }) {
  const { t, tError, lang } = useLanguage()
  const qc = useQueryClient()
  const { data } = useQuery<{ contexts: Ctx[] }>({ queryKey: ['course-lti', courseId], queryFn: () => ltiApi.course(courseId) })
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const run = async (k: string, fn: () => Promise<string>) => {
    setBusy(k); setMsg(null)
    try {
      setMsg({ ok: true, text: await fn() })
      qc.invalidateQueries({ queryKey: ['course-lti', courseId] })
      qc.invalidateQueries({ queryKey: ['members', courseId] })
      qc.invalidateQueries({ queryKey: ['course', courseId] })
    } catch (err: any) { setMsg({ ok: false, text: tError(err.response?.data?.detail, 'lti.failed') }) } finally { setBusy('') }
  }
  if (!data) return null
  if (data.contexts.length === 0) {
    if (hideWhenUnlinked) return null
    return (
      <section className="card p-4 flex gap-3 items-start">
        <IconTile tone="ink" size="sm"><School size={15} /></IconTile>
        <div>
          <h2 className="font-bold">{t('lti.course.notLinked')}</h2>
          <p className="text-[13px] text-ink-muted mt-0.5 max-w-2xl">{t('lti.course.notLinkedHint')}</p>
        </div>
      </section>
    )
  }
  return (
    <section className="card p-5 space-y-3" aria-labelledby="moodle-title">
      <div className="flex items-start gap-3">
        <IconTile tone="marker"><School size={19} /></IconTile>
        <div className="min-w-0 flex-1">
          <h2 id="moodle-title" className="font-extrabold">{t('lti.course.title')}</h2>
          <p className="text-[13px] text-ink-muted">{t('lti.course.intro')}</p>
        </div>
      </div>
      {data.contexts.map((c) => (
        <div key={c.id} className="rounded-lg border-2 border-line bg-paper/50 px-3.5 py-3">
          <p className="font-bold flex flex-wrap items-center gap-2">
            {c.label && <span className="font-mono text-[11px] font-bold bg-ink text-white rounded px-1.5 py-0.5">{c.label}</span>}
            {c.title} <span className="text-[12px] font-semibold text-ink-muted">· {c.platform}</span>
          </p>
          <p className="mt-1 text-[12.5px] text-ink-muted">
            {t('lti.course.rosterAt', { when: c.last_roster_sync ? relative(c.last_roster_sync, lang) : t('lti.course.never') })} ·{' '}
            {t('lti.course.gradesAt', { when: c.last_grade_sync ? relative(c.last_grade_sync, lang) : t('lti.course.never') })}
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            <button className="btn-secondary btn-sm" disabled={!!busy || !c.roster} title={c.roster ? '' : t('lti.course.noRoster')}
              onClick={() => run('r', async () => { const r = await ltiApi.roster(courseId); return t('lti.course.rosterDone', r) })}>
              {busy === 'r' ? <Loader2 size={14} className="animate-spin" /> : <Users size={14} />} {t('lti.course.roster')}
            </button>
            <button className="btn-primary btn-sm" disabled={!!busy || !c.grades} title={c.grades ? '' : t('lti.course.noGrades')}
              onClick={() => run('g', async () => { const r = await ltiApi.grades(courseId); return t('lti.course.gradesDone', r) })}>
              {busy === 'g' ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} {t('lti.course.grades')}
            </button>
            {teacher && (
              <button className="btn-ghost btn-sm sm:ml-auto hover:text-bad" disabled={!!busy}
                onClick={() => { if (confirm(t('lti.course.unlinkConfirm'))) run('u', async () => { await ltiApi.unlink(courseId, c.id); return t('lti.course.unlinked') }) }}>
                <Unlink size={14} /> {t('lti.course.unlink')}
              </button>
            )}
          </div>
        </div>
      ))}
      <p className="text-[12.5px] text-ink-muted">{t('lti.course.gradesRule')}</p>
      {msg && <p role="status" className={`text-sm font-semibold rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
    </section>
  )
}
