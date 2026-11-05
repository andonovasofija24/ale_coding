import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, BookOpen, CheckCircle2, ExternalLink, GraduationCap, Link2, Loader2, Plus, School, Send } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { ltiApi } from '../services/api'
import { formatDateTime } from '../lib/time'
import { IconTile } from '../components/EmptyState'
import { KindBadge } from '../components/course/bits'
import { AssignmentKind } from '../types'

/**
 * Where a launch from Moodle (courses.finki) lands. The backend has checked Moodle's signed message and put the
 * result in the URL fragment: the sign-in token and what to do next — open a page, link a new Moodle course to an
 * ALE course (the first teacher launch), or pick what to add to the Moodle course ("Select content").
 */
export default function LtiPage() {
  const { loginWithToken } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const done = useRef(false)
  const [state, setState] = useState<{ kind: 'wait' } | { kind: 'error'; code: string } | { kind: 'setup'; s: string; d?: string } | { kind: 'deeplink'; d: string }>({ kind: 'wait' })

  useEffect(() => {
    if (done.current) return
    done.current = true
    const q = new URLSearchParams(window.location.search)
    const h = new URLSearchParams(window.location.hash.slice(1))
    history.replaceState(null, '', window.location.pathname) // the token never stays in the address bar
    if (q.get('error')) { setState({ kind: 'error', code: q.get('error')! }); return }
    const token = h.get('token')
    if (!token) { setState({ kind: 'error', code: 'expired' }); return }
    loginWithToken(token).then(() => {
      if (h.get('deeplink')) setState({ kind: 'deeplink', d: h.get('deeplink')! })
      else if (h.get('setup')) setState({ kind: 'setup', s: h.get('setup')! })
      else navigate(h.get('next') || '/courses', { replace: true })
    }).catch(() => setState({ kind: 'error', code: 'expired' }))
  }, [loginWithToken, navigate])

  return (
    <div className="min-h-screen bg-paper">
      <header className="bg-surface border-b-2 border-ink">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-3">
          <span className="font-extrabold text-lg tracking-tight">ALE</span>
          <span className="text-ink-faint">×</span>
          <span className="text-sm font-semibold text-ink-muted flex items-center gap-1.5"><School size={15} /> courses.finki</span>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {state.kind === 'wait' && <p className="flex items-center gap-2 text-ink-muted"><Loader2 className="animate-spin" size={18} /> {t('sso.signingIn')}</p>}
        {state.kind === 'error' && <LtiError code={state.code} />}
        {state.kind === 'setup' && <Setup s={state.s} onDone={(id) => {
          const d = state.d  // came from "Select content": back to choosing once the course is linked
          if (d) setState({ kind: 'deeplink', d }); else navigate(`/courses/${id}`, { replace: true })
        }} />}
        {state.kind === 'deeplink' && <DeepLink d={state.d} onSetup={(s) => setState({ kind: 'setup', s, d: state.d })} />}
      </main>
    </div>
  )
}

function LtiError({ code }: { code: string }) {
  const { t } = useLanguage()
  const known = ['course_not_ready', 'unknown_platform', 'unknown_deployment', 'expired', 'not_instructor', 'email_taken', 'anonymous']
  const k = known.includes(code) ? code : 'generic'
  return (
    <section className="card-stamp p-6 flex gap-4" role="alert">
      <IconTile tone="bad"><AlertTriangle size={19} /></IconTile>
      <div>
        <h1 className="font-extrabold text-xl">{t(`lti.err.${k}.title` as any)}</h1>
        <p className="mt-2 text-ink-soft leading-relaxed">{t(`lti.err.${k}.body` as any)}</p>
        {k === 'generic' && <p className="mt-2 text-[12px] font-mono text-ink-muted">{code}</p>}
      </div>
    </section>
  )
}

interface SetupInfo {
  label: string; title: string; course_id: string | null
  subject: { id: string; code: string; name: string } | null
  courses: { id: string; code: string; name: string; semester: string; linked: boolean; suggested: boolean }[]
}

/** The first time a teacher opens ALE from a Moodle course: make an ALE course for it, or link one they have. */
function Setup({ s, onDone }: { s: string; onDone: (courseId: string) => void }) {
  const { t, tError } = useLanguage()
  const admin = useAuth().user?.role === 'admin'   // only the admin makes courses; a professor links one of theirs
  const [info, setInfo] = useState<SetupInfo | null>(null)
  const [choice, setChoice] = useState<string>('new')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  useEffect(() => {
    ltiApi.setupInfo(s).then((x: SetupInfo) => {
      if (x.course_id) { onDone(x.course_id); return }
      setInfo(x)
      const hit = x.courses.find((c) => c.suggested && !c.linked) ?? (admin ? undefined : x.courses.find((c) => !c.linked))
      if (hit) setChoice(hit.id)
    })
      .catch((e) => setErr(tError(e.response?.data?.detail, 'lti.failed')))
  }, [s]) // eslint-disable-line react-hooks/exhaustive-deps
  const go = async () => {
    setBusy(true); setErr('')
    try { onDone((await ltiApi.setup(s, choice === 'new' ? null : choice)).course_id) } catch (e: any) {
      setErr(tError(e.response?.data?.detail, 'lti.failed')); setBusy(false)
    }
  }
  if (err && !info) return <p role="alert" className="text-bad">{err}</p>
  if (!info) return <Loader2 className="animate-spin text-ink-muted" />
  const free = info.courses.filter((c) => !c.linked)
  return (
    <section>
      <div className="flex items-start gap-4">
        <IconTile tone="marker" size="lg"><Link2 size={24} /></IconTile>
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{t('lti.setup.title')}</h1>
          <p className="mt-1 text-ink-muted">{t('lti.setup.intro')}</p>
        </div>
      </div>
      <div className="mt-6 card p-4 flex items-center gap-3">
        <span className="font-mono text-[12px] font-bold bg-ink text-white rounded px-1.5 py-0.5">{info.label || 'Moodle'}</span>
        <span className="font-bold">{info.title}</span>
      </div>
      <fieldset className="mt-6 space-y-2">
        <legend className="field-label">{t('lti.setup.choose')}</legend>
        {admin && <Choice checked={choice === 'new'} onChange={() => setChoice('new')} icon={<Plus size={16} />}
          title={t('lti.setup.new')} text={info.subject ? t('lti.setup.newSubject', { subject: `${info.subject.code} — ${info.subject.name}` }) : t('lti.setup.newHint')} />}
        {!admin && free.length === 0 && <p className="card px-4 py-3 text-[13.5px] text-ink-soft">{t('lti.setup.askAdmin')}</p>}
        {free.map((c) => (
          <Choice key={c.id} checked={choice === c.id} onChange={() => setChoice(c.id)} icon={<GraduationCap size={16} />}
            title={`${c.code} — ${c.name}`} text={[t('lti.setup.link'), c.semester, c.suggested ? t('lti.setup.sameSubject') : ''].filter(Boolean).join(' · ')} />
        ))}
      </fieldset>
      {err && <p role="alert" className="mt-3 text-sm text-bad">{err}</p>}
      <button className="btn-primary mt-6" disabled={busy || (!admin && choice === 'new')} onClick={go}>
        {busy ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />} {t('lti.setup.go')}
      </button>
      <p className="mt-4 text-[13px] text-ink-muted max-w-xl">{t('lti.setup.after')}</p>
    </section>
  )
}

function Choice({ checked, onChange, icon, title, text }: { checked: boolean; onChange: () => void; icon: React.ReactNode; title: string; text: string }) {
  return (
    <label className={`flex items-start gap-3 rounded-xl border-2 px-4 py-3 cursor-pointer bg-surface ${checked ? 'border-ink shadow-stamp-sm' : 'border-line hover:border-line-strong'}`}>
      <input type="radio" className="mt-1 accent-[#2747C9]" checked={checked} onChange={onChange} />
      <span className="mt-0.5 text-ink-muted">{icon}</span>
      <span><span className="block font-bold">{title}</span><span className="block text-[13px] text-ink-muted">{text}</span></span>
    </label>
  )
}

interface DLInfo {
  label: string; title: string; multiple: boolean; setup: string | null
  course: { id: string; code: string; name: string } | null
  assignments: { id: string; title: string; kind: AssignmentKind; published: boolean; due_at: string | null }[]
}

/** "Select content" in Moodle: each chosen assignment becomes a Moodle activity with its own gradebook column. */
function DeepLink({ d, onSetup }: { d: string; onSetup: (s: string) => void }) {
  const { t, tError, lang } = useLanguage()
  const [info, setInfo] = useState<DLInfo | null>(null)
  const [picked, setPicked] = useState<string[]>([])
  const [courseLink, setCourseLink] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const form = useRef<HTMLFormElement>(null)
  const [resp, setResp] = useState<{ return_url: string; jwt: string } | null>(null)
  useEffect(() => {
    ltiApi.deeplinkInfo(d).then((x: DLInfo) => { if (x.setup) onSetup(x.setup); else setInfo(x) })
      .catch((e) => setErr(tError(e.response?.data?.detail, 'lti.failed')))
  }, [d]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (resp) form.current?.submit() }, [resp])
  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : info?.multiple ? [...p, id] : [id]))
  const send = async () => {
    setBusy(true); setErr('')
    try { setResp(await ltiApi.deeplink(d, picked, courseLink)) } catch (e: any) {
      setErr(tError(e.response?.data?.detail, 'lti.failed')); setBusy(false)
    }
  }
  if (err && !info) return <p role="alert" className="text-bad">{err}</p>
  if (!info) return <Loader2 className="animate-spin text-ink-muted" />
  return (
    <section>
      <div className="flex items-start gap-4">
        <IconTile tone="cobalt" size="lg"><BookOpen size={24} /></IconTile>
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{t('lti.dl.title')}</h1>
          <p className="mt-1 text-ink-muted">{t('lti.dl.intro', { course: info.course ? info.course.name : info.title })}</p>
        </div>
      </div>
      <div className="mt-6 space-y-2">
        <Check checked={courseLink} onChange={() => setCourseLink(!courseLink)} title={t('lti.dl.course')} text={t('lti.dl.courseHint')} icon={<GraduationCap size={16} />} />
        {info.assignments.length === 0 && <p className="text-sm text-ink-muted px-1 py-3">{t('lti.dl.none')}</p>}
        {info.assignments.map((a) => (
          <Check key={a.id} checked={picked.includes(a.id)} onChange={() => toggle(a.id)} icon={<ExternalLink size={16} />}
            title={a.title} badge={<KindBadge kind={a.kind} />}
            text={[a.due_at ? t('lti.dl.due', { when: formatDateTime(a.due_at, lang) }) : '', a.published ? '' : t('lti.dl.draft')].filter(Boolean).join(' · ') || t('lti.dl.gradeColumn')} />
        ))}
      </div>
      {err && <p role="alert" className="mt-3 text-sm text-bad">{err}</p>}
      <button className="btn-primary mt-6" disabled={busy || (!courseLink && picked.length === 0)} onClick={send}>
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />} {t('lti.dl.add', { n: picked.length + (courseLink ? 1 : 0) })}
      </button>
      <p className="mt-4 text-[13px] text-ink-muted max-w-xl">{t('lti.dl.after')}</p>
      {resp && (
        <form ref={form} method="post" action={resp.return_url} className="hidden">
          <input type="hidden" name="JWT" value={resp.jwt} />
        </form>
      )}
    </section>
  )
}

function Check({ checked, onChange, icon, title, text, badge }: { checked: boolean; onChange: () => void; icon: React.ReactNode; title: string; text: string; badge?: React.ReactNode }) {
  return (
    <label className={`flex items-start gap-3 rounded-xl border-2 px-4 py-3 cursor-pointer bg-surface ${checked ? 'border-ink shadow-stamp-sm' : 'border-line hover:border-line-strong'}`}>
      <input type="checkbox" className="mt-1 accent-[#2747C9]" checked={checked} onChange={onChange} />
      <span className="mt-0.5 text-ink-muted">{icon}</span>
      <span className="min-w-0"><span className="flex items-center gap-2 font-bold">{title} {badge}</span><span className="block text-[13px] text-ink-muted">{text}</span></span>
    </label>
  )
}
