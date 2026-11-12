import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { BellRing, Loader2, Save } from 'lucide-react'
import GradingSchemeCard from './GradingSchemeCard'
import { coursesApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { CourseDetail } from '../../types'

/** Admin: the space's name / code / school year / description (its subject never changes); archive. */
export default function SettingsTab({ course }: { course: CourseDetail }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [f, setF] = useState({ code: course.code, name: course.name, semester: course.semester, description: course.description })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const save = async (data: object) => {
    setSaving(true); setMsg(null)
    try {
      await coursesApi.update(course.id, data)
      qc.invalidateQueries({ queryKey: ['course', course.id] })
      qc.invalidateQueries({ queryKey: ['courses'] })
      setMsg({ ok: true, text: t('course.saved') })
    } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'course.actionFailed') })
    } finally { setSaving(false) }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <form className="card p-5 sm:p-6 space-y-4" onSubmit={(e) => { e.preventDefault(); save(f) }}>
        <div className="grid sm:grid-cols-[9rem_minmax(0,1fr)] gap-3">
          <div>
            <label htmlFor="s-code" className="field-label">{t('courses.code')}</label>
            <input id="s-code" className="input" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} required maxLength={50} />
          </div>
          <div>
            <label htmlFor="s-name" className="field-label">{t('courses.name')}</label>
            <input id="s-name" className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required maxLength={300} />
          </div>
        </div>
        <div>
          <label htmlFor="s-sem" className="field-label">{t('courses.semester')}</label>
          <input id="s-sem" className="input" value={f.semester} onChange={(e) => setF({ ...f, semester: e.target.value })} maxLength={100} />
        </div>
        <div>
          <label htmlFor="s-desc" className="field-label">{t('courses.description')}</label>
          <textarea id="s-desc" rows={4} className="input h-auto py-2" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
        </div>
        {msg && <p role="status" className={`text-sm rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('common.save')}
        </button>
      </form>

      <CommunicationCard course={course} />

      <GradingSchemeCard courseId={course.id} />

      <section className="card p-5 sm:p-6">
        <h2 className="font-bold">{course.archived ? t('course.unarchive') : t('course.archive')}</h2>
        <p className="mt-1 text-[13px] text-ink-muted">{t('course.archiveHint')}</p>
        <button className="btn-secondary mt-3" disabled={saving}
          onClick={() => (course.archived || confirm(t('course.archiveConfirm'))) && save({ archived: !course.archived })}>
          {course.archived ? t('course.unarchive') : t('course.archive')}
        </button>
      </section>
    </div>
  )
}

/** Teaching language (e-mails, grade sheet) and automatic deadline reminders. */
function CommunicationCard({ course }: { course: CourseDetail }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [f, setF] = useState({
    language: course.language ?? 'mk', reminders_enabled: course.reminders_enabled ?? true, reminder_hours: course.reminder_hours ?? 24,
  })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const save = async () => {
    setSaving(true); setMsg(null)
    try {
      await coursesApi.update(course.id, f)
      qc.invalidateQueries({ queryKey: ['course', course.id] })
      setMsg({ ok: true, text: t('course.saved') })
    } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'course.actionFailed') })
    } finally { setSaving(false) }
  }
  return (
    <section className="card p-5 sm:p-6 space-y-4">
      <div>
        <h2 className="font-bold flex items-center gap-2"><BellRing size={17} /> {t('comm.title')}</h2>
        <p className="mt-1 text-[13px] text-ink-muted">{t('comm.hint')}</p>
      </div>
      <div>
        <span className="field-label">{t('comm.language')}</span>
        <div className="inline-flex rounded-lg border border-line p-0.5" role="radiogroup" aria-label={t('comm.language')}>
          {(['mk', 'en'] as const).map((l) => (
            <button key={l} type="button" role="radio" aria-checked={f.language === l} onClick={() => setF({ ...f, language: l })}
              className={`h-8 px-3 rounded-md text-[13px] font-semibold ${f.language === l ? 'bg-ink text-white' : 'text-ink-muted hover:text-ink'}`}>
              {l === 'mk' ? t('course.langMk') : t('course.langEn')}
            </button>
          ))}
        </div>
        <p className="mt-1.5 text-[12px] text-ink-muted">{t('comm.languageHint')}</p>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <label className="inline-flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" className="w-4 h-4 accent-cobalt" checked={f.reminders_enabled}
            onChange={(e) => setF({ ...f, reminders_enabled: e.target.checked })} />
          {t('comm.reminders')}
        </label>
        <label className="inline-flex items-center gap-2 text-sm text-ink-soft">
          <input type="number" min={1} max={168} value={f.reminder_hours} disabled={!f.reminders_enabled}
            onChange={(e) => setF({ ...f, reminder_hours: Number(e.target.value) })} className="input h-8 w-20 text-right tabular-nums" />
          {t('comm.hoursBefore')}
        </label>
      </div>
      <p className="text-[12px] text-ink-muted -mt-2">{t('comm.remindersHint')}</p>
      {msg && <p role="status" className={`text-sm rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
      <button className="btn-primary" disabled={saving || f.reminder_hours < 1 || f.reminder_hours > 168} onClick={save}>
        {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('common.save')}
      </button>
    </section>
  )
}
