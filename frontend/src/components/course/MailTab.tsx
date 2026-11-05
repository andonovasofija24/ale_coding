import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, BellRing, Check, Eye, Loader2, Mail, Paperclip, Plus, Save, Send, Sparkles, Users, X } from 'lucide-react'
import { mailApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { CourseDetail, CourseEmail, EmailStatus } from '../../types'
import { formatDateTime } from '../../lib/time'

interface MailList { mode: 'preview' | 'smtp' | 'microsoft'; configured: boolean; reminders_sent: number; emails: CourseEmail[] }

const STATUS_TONE: Record<EmailStatus, string> = {
  draft: 'bg-cobalt-soft text-cobalt',
  sending: 'bg-line-soft text-ink-soft',
  sent: 'bg-ok-soft text-ok',
  cancelled: 'bg-paper text-ink-muted border border-line',
}

/** Staff: messages to the students (or the staff). Drafts appear by themselves when something happens in the course;
 *  nothing is sent until someone reads it and presses Send. Each student gets the version in their group's language. */
export default function MailTab({ course }: { course: CourseDetail }) {
  const { t, lang } = useLanguage()
  const qc = useQueryClient()
  const { data, isLoading } = useQuery<MailList>({
    queryKey: ['emails', course.id], queryFn: () => mailApi.list(course.id),
    refetchInterval: (q) => ((q.state.data as MailList | undefined)?.emails.some((e) => e.status === 'sending') ? 2000 : false),
  })
  const [selected, setSelected] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!selected && data?.emails.length) setSelected((data.emails.find((e) => e.status === 'draft') ?? data.emails[0]).id)
  }, [data, selected])

  if (isLoading || !data) return <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>

  const newMessage = async () => {
    setCreating(true)
    try {
      const e = await mailApi.create(course.id, { audience: 'students', subject_mk: `[${course.code}] `, body_mk: '', subject_en: `[${course.code}] `, body_en: '' })
      await qc.invalidateQueries({ queryKey: ['emails', course.id] })
      setSelected(e.id)
    } finally { setCreating(false) }
  }
  const drafts = data.emails.filter((e) => e.status === 'draft')
  const rest = data.emails.filter((e) => e.status !== 'draft')

  return (
    <div>
      <div className="flex flex-wrap items-start gap-3">
        <p className="text-sm text-ink-muted flex-1 min-w-[16rem]">{t('mail.hint')}</p>
        <button className="btn-primary" onClick={newMessage} disabled={creating}>
          {creating ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />} {t('mail.new')}
        </button>
      </div>

      {data.mode === 'preview' && (
        <p className="mt-4 flex items-start gap-2 text-[13px] rounded-lg bg-cobalt-soft text-cobalt px-3 py-2.5">
          <Eye size={16} className="shrink-0 mt-px" /> {t('mail.previewMode')}
        </p>
      )}
      {data.mode !== 'preview' && !data.configured && (
        <p className="mt-4 flex items-start gap-2 text-[13px] rounded-lg bg-bad-soft text-bad px-3 py-2.5">
          <AlertTriangle size={16} className="shrink-0 mt-px" /> {t('mail.notConfigured')}
        </p>
      )}

      <div className="mt-4 grid lg:grid-cols-[19rem_minmax(0,1fr)] gap-4 items-start">
        <aside className="card overflow-hidden">
          <ListSection title={t('mail.drafts', { n: drafts.length })} items={drafts} selected={selected} onSelect={setSelected} empty={t('mail.noDrafts')} />
          <ListSection title={t('mail.history')} items={rest} selected={selected} onSelect={setSelected} empty={t('mail.noHistory')} />
          <p className="px-4 py-3 border-t border-line-soft text-[12px] text-ink-muted flex items-center gap-1.5">
            <BellRing size={13} /> {course.reminders_enabled === false ? t('mail.remindersOff')
              : t('mail.remindersSent', { n: data.reminders_sent, h: course.reminder_hours ?? 24 })}
          </p>
        </aside>
        {selected ? <EmailPanel key={selected} id={selected} course={course} lang={lang} /> : (
          <div className="card px-6 py-14 text-center text-ink-muted">
            <Mail className="mx-auto mb-2 text-ink-faint" /> {t('mail.empty')}
          </div>
        )}
      </div>
    </div>
  )
}

function ListSection({ title, items, selected, onSelect, empty }: {
  title: string; items: CourseEmail[]; selected: string | null; onSelect: (id: string) => void; empty: string
}) {
  const { t, lang } = useLanguage()
  return (
    <div className="border-b border-line-soft last:border-b-0">
      <h3 className="panel-title px-4 pt-3 pb-1.5">{title}</h3>
      {items.length === 0 ? <p className="px-4 pb-3 text-[13px] text-ink-faint">{empty}</p> : (
        <ul className="max-h-[22rem] overflow-y-auto">
          {items.map((e) => (
            <li key={e.id}>
              <button onClick={() => onSelect(e.id)} aria-current={selected === e.id}
                className={`w-full text-left px-4 py-2.5 border-l-[3px] transition-colors ${selected === e.id ? 'border-cobalt bg-cobalt-soft/50' : 'border-transparent hover:bg-paper/70'}`}>
                <span className="flex items-center gap-1.5 text-[11px] font-semibold">
                  <span className="uppercase tracking-wide text-ink-muted">{t(`mailkind.${e.kind}` as any)}</span>
                  {e.audience === 'staff' && <span className="text-obj">· {t('mail.toStaff')}</span>}
                  <span className={`ml-auto rounded-full px-1.5 py-px ${STATUS_TONE[e.status]}`}>{t(`mailstatus.${e.status}` as any)}</span>
                </span>
                <span className="block mt-0.5 text-sm font-medium truncate">{(lang === 'en' ? e.subject_en || e.subject_mk : e.subject_mk || e.subject_en) || '—'}</span>
                <span className="block text-[12px] text-ink-muted truncate">
                  {e.assignment_title ? `${e.assignment_title} · ` : ''}
                  {formatDateTime(e.sent_at ?? e.created_at, lang)}
                  {e.status === 'sent' ? ` · ${t('mail.recipientsN', { n: e.recipients })}` : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function EmailPanel({ id, course, lang }: { id: string; course: CourseDetail; lang: 'mk' | 'en' }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const { data: e, isLoading } = useQuery<CourseEmail>({
    queryKey: ['email', id], queryFn: () => mailApi.get(id),
    refetchInterval: (q) => ((q.state.data as CourseEmail | undefined)?.status === 'sending' ? 1500 : false),
  })
  const [f, setF] = useState<{ subject_mk: string; body_mk: string; subject_en: string; body_en: string; audience: 'students' | 'staff'; group_id: string | null } | null>(null)
  const [tab, setTab] = useState<'mk' | 'en'>(course.language === 'en' ? 'en' : 'mk')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState<'' | 'save' | 'ai' | 'send' | 'cancel'>('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (e && !f) setF({ subject_mk: e.subject_mk, body_mk: e.body_mk ?? '', subject_en: e.subject_en, body_en: e.body_en ?? '',
                        audience: e.audience, group_id: e.group_id })
  }, [e, f])

  if (isLoading || !e) return <div className="card p-10 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>

  const refresh = async (fresh?: CourseEmail) => {
    if (fresh) qc.setQueryData(['email', id], fresh)
    else await qc.invalidateQueries({ queryKey: ['email', id] })
    qc.invalidateQueries({ queryKey: ['emails', course.id] })
  }
  const run = async (kind: typeof busy, fn: () => Promise<any>, ok?: string) => {
    setBusy(kind); setMsg(null)
    try {
      const r = await fn()
      if (ok) setMsg({ ok: true, text: ok })
      return r
    } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'mail.failed') })
    } finally { setBusy('') }
  }
  const dirty = !!f && (f.subject_mk !== e.subject_mk || f.body_mk !== (e.body_mk ?? '') || f.subject_en !== e.subject_en
    || f.body_en !== (e.body_en ?? '') || f.audience !== e.audience || f.group_id !== e.group_id)
  const save = async () => { const r = await run('save', () => mailApi.update(id, f!), t('mail.saved')); if (r) await refresh(r) }

  // ---- a sent / cancelled message: read-only, with who got it --------------------------------------------------
  if (e.status !== 'draft') {
    const failed = (e.deliveries ?? []).filter((d) => d.status === 'failed')
    return (
      <article className="card p-5 sm:p-6 min-w-0">
        <Header e={e} />
        <div className="mt-4 grid md:grid-cols-2 gap-3">
          {(['mk', 'en'] as const).map((l) => (
            <div key={l} className="rounded-lg border border-line p-3 min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-wide text-ink-muted">{l === 'mk' ? t('course.langMk') : t('course.langEn')}</p>
              <p className="mt-1 font-semibold break-words">{(l === 'mk' ? e.subject_mk : e.subject_en) || <span className="text-ink-faint">—</span>}</p>
              <pre className="mt-1.5 whitespace-pre-wrap break-words font-sans text-[13px] text-ink-soft">{(l === 'mk' ? e.body_mk : e.body_en) || '—'}</pre>
            </div>
          ))}
        </div>
        {e.status !== 'cancelled' && (
          <>
            <h3 className="panel-title mt-5 mb-2">
              {e.status === 'sending' ? t('mail.sendingNow') : t('mail.deliveries', { n: e.recipients })}
              {failed.length > 0 && <span className="ml-2 text-bad">· {t('mail.failedN', { n: failed.length })}</span>}
            </h3>
            <div className="rounded-lg border border-line max-h-72 overflow-y-auto">
              <table className="w-full text-[13px]">
                <tbody>
                  {(e.deliveries ?? []).map((d) => (
                    <tr key={d.address} className="border-b border-line-soft last:border-0">
                      <td className="px-3 py-1.5 truncate max-w-[16rem]">{d.address}</td>
                      <td className="px-3 py-1.5 text-[11px] font-bold uppercase text-ink-muted">{d.lang}</td>
                      <td className="px-3 py-1.5 text-right">
                        <span className={d.status === 'failed' ? 'text-bad font-semibold' : d.status === 'sent' ? 'text-ok' : 'text-ink-muted'} title={d.error || undefined}>
                          {t(`delivery.${d.status}` as any)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {failed[0] && <p className="mt-2 text-[12px] text-bad break-words">{failed[0].error}</p>}
          </>
        )}
      </article>
    )
  }

  // ---- a draft: edit both languages, let AI improve it, approve ------------------------------------------------
  if (!f) return null
  const subjectKey = tab === 'mk' ? 'subject_mk' : 'subject_en'
  const bodyKey = tab === 'mk' ? 'body_mk' : 'body_en'
  const reach = e.would_reach
  const emptyOther = tab === 'mk' ? !f.subject_en.trim() && !f.body_en.trim() : !f.subject_mk.trim() && !f.body_mk.trim()
  const canSend = (f.subject_mk.trim() || f.subject_en.trim()) && (f.body_mk.trim() || f.body_en.trim())

  return (
    <article className="card p-5 sm:p-6 min-w-0">
      <Header e={e} />

      <div className="mt-4 grid sm:grid-cols-2 gap-3">
        <div>
          <label className="field-label" htmlFor="m-aud">{t('mail.audience')}</label>
          <select id="m-aud" className="input" value={f.audience}
            onChange={(ev) => setF({ ...f, audience: ev.target.value as any, group_id: ev.target.value === 'staff' ? null : f.group_id })}>
            <option value="students">{t('mail.toStudents')}</option>
            <option value="staff">{t('mail.toStaffLong')}</option>
          </select>
        </div>
        {f.audience === 'students' && course.groups.length > 0 && (
          <div>
            <label className="field-label" htmlFor="m-grp">{t('course.group')}</label>
            <select id="m-grp" className="input" value={f.group_id ?? ''} onChange={(ev) => setF({ ...f, group_id: ev.target.value || null })}>
              <option value="">{t('course.allGroups')}</option>
              {course.groups.map((g) => <option key={g.id} value={g.id}>{g.name}{g.language ? ` (${g.language.toUpperCase()})` : ''}</option>)}
            </select>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-end gap-1 border-b border-line">
        {(['mk', 'en'] as const).map((l) => (
          <button key={l} onClick={() => setTab(l)}
            className={`h-9 px-3 text-sm font-semibold border-b-2 -mb-px ${tab === l ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink'}`}>
            {l === 'mk' ? t('course.langMk') : t('course.langEn')}
            {reach && <span className="ml-1.5 text-[11px] font-normal text-ink-muted tabular-nums">· {reach[l]}</span>}
          </button>
        ))}
      </div>
      <div className="mt-3 space-y-3">
        <div>
          <label className="field-label" htmlFor="m-subj">{t('mail.subject')}</label>
          <input id="m-subj" className="input" maxLength={300} value={f[subjectKey]} onChange={(ev) => setF({ ...f, [subjectKey]: ev.target.value })} />
        </div>
        <div>
          <label className="field-label" htmlFor="m-body">{t('mail.body')}</label>
          <textarea id="m-body" rows={10} className="input h-auto py-2 leading-relaxed" value={f[bodyKey]}
            onChange={(ev) => setF({ ...f, [bodyKey]: ev.target.value })} />
        </div>
        {emptyOther && reach && reach[tab === 'mk' ? 'en' : 'mk'] > 0 && (
          <p className="text-[12px] text-ink-muted">{t('mail.otherEmpty')}</p>
        )}
        {e.kind === 'gradesheet' && (
          <p className="flex items-center gap-1.5 text-[13px] text-ink-soft"><Paperclip size={14} /> {t('mail.gradesheetAttached')}</p>
        )}
      </div>

      {/* AI */}
      <div className="mt-4 rounded-lg bg-paper/70 border border-line-soft p-3">
        <label className="field-label flex items-center gap-1.5" htmlFor="m-ai"><Sparkles size={14} className="text-obj" /> {t('mail.aiTitle')}</label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input id="m-ai" className="input" maxLength={1000} value={notes} placeholder={t('mail.aiPlaceholder')} onChange={(ev) => setNotes(ev.target.value)} />
          <button className="btn-secondary whitespace-nowrap" disabled={!!busy} onClick={async () => {
            if (dirty) { const s = await run('save', () => mailApi.update(id, f)); if (!s) return }
            const r = await run('ai', () => mailApi.improve(id, notes), t('mail.aiDone'))
            if (r) { setF({ subject_mk: r.subject_mk, body_mk: r.body_mk, subject_en: r.subject_en, body_en: r.body_en, audience: r.audience, group_id: r.group_id }); await refresh(r) }
          }}>
            {busy === 'ai' ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {t('mail.aiButton')}
          </button>
        </div>
        <p className="mt-1.5 text-[12px] text-ink-muted">{t('mail.aiHint')}</p>
      </div>

      {msg && <p role="status" className={`mt-4 text-sm rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button className="btn-secondary" disabled={!!busy || !dirty} onClick={save}>
          {busy === 'save' ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('common.save')}
        </button>
        {!confirming ? (
          <button className="btn-primary" disabled={!!busy || !canSend} onClick={() => setConfirming(true)}>
            <Send size={15} /> {t('mail.send')}
          </button>
        ) : (
          <span className="inline-flex flex-wrap items-center gap-2 rounded-lg bg-cobalt-soft px-2 py-1">
            <span className="text-[13px] text-cobalt font-semibold px-1">
              <Users size={14} className="inline -mt-0.5 mr-1" />
              {dirty ? t('mail.saveFirst') : t('mail.confirmSend', { n: reach?.total ?? 0, mk: reach?.mk ?? 0, en: reach?.en ?? 0 })}
            </span>
            <button className="btn-primary btn-sm" disabled={!!busy || !reach?.total} onClick={async () => {
              if (dirty) { const s = await run('save', () => mailApi.update(id, f)); if (!s) return; await refresh(s); return }
              const r = await run('send', () => mailApi.send(id), t('mail.sent'))
              setConfirming(false)
              if (r) await refresh()
            }}>
              {busy === 'send' || busy === 'save' ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              {dirty ? t('common.save') : t('mail.sendNow')}
            </button>
            <button className="btn-ghost btn-sm" onClick={() => setConfirming(false)} aria-label={t('mail.back')}><X size={14} /></button>
          </span>
        )}
        <span className="flex-1" />
        <button className="btn-ghost text-bad hover:bg-bad-soft hover:text-bad" disabled={!!busy}
          onClick={async () => { if (confirm(t('mail.cancelConfirm'))) { const r = await run('cancel', () => mailApi.cancel(id)); if (r) await refresh() } }}>
          {t('mail.discard')}
        </button>
      </div>
      {reach && <p className="mt-2 text-[12px] text-ink-muted">{t('mail.wouldReach', { n: reach.total, mk: reach.mk, en: reach.en })}</p>}
    </article>
  )
}

function Header({ e }: { e: CourseEmail }) {
  const { t, lang } = useLanguage()
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-[11px] font-bold uppercase tracking-wide text-ink-muted">{t(`mailkind.${e.kind}` as any)}</span>
      <span className={`text-[11px] font-semibold rounded-full px-2 py-0.5 ${STATUS_TONE[e.status]}`}>{t(`mailstatus.${e.status}` as any)}</span>
      {e.assignment_title && <span className="text-[13px] text-ink-soft truncate">· {e.assignment_title}</span>}
      {e.attachment_name && <span className="inline-flex items-center gap-1 text-[12px] text-ink-muted"><Paperclip size={12} /> {e.attachment_name}</span>}
      <span className="ml-auto text-[12px] text-ink-muted">
        {e.status === 'draft' ? (e.kind !== 'custom' ? t('mail.autoDraft') : t('mail.draftSince', { when: formatDateTime(e.created_at, lang) }))
          : e.sent_at ? formatDateTime(e.sent_at, lang) : ''}
      </span>
    </div>
  )
}
