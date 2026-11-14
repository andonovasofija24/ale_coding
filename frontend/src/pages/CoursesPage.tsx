import { useMemo, useState } from 'react'
import { permLabel } from '../components/PermissionsEditor'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, ArrowRight, CalendarClock, ChevronRight, GraduationCap, Lock, Plus, Search, Send, Sparkles, Users, X, Loader2 } from 'lucide-react'
import { coursesApi, electivesApi, sessionsApi, subjectsApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Course, ElectivePlan, ElectiveRequest, SubjectSummary } from '../types'
import { relative, formatDateTime } from '../lib/time'
import AppHeader from '../components/AppHeader'
import SubjectIcon from '../components/SubjectIcon'
import AccessCard from '../components/AccessCard'
import SubjectForm from '../components/SubjectForm'
import { langClass } from '../lib/languages'

interface Overview {
  continue: { task_id: string; title: string; language: string; completed_steps: number; total_steps: number; updated_at: string } | null
  completed: number
  in_progress: number
}
type Mode = 'mine' | 'tasks' | 'all' | 'elective' | string  // a semester: '1'…'8'
const SEMS = ['1', '2', '3', '4', '5', '6', '7', '8']

/**
 * Home ("Предмети"): the person's access card and console (where they stopped, their courses), then the whole
 * FINKI catalogue along the eight semesters of the studies. Courses and the people in them are set by the admin, who
 * also adds new subjects to the catalogue. A student puts electives into their own semesters (the card's semester,
 * "Add an elective", or drag and drop) — every change (add, take out, move) is a request the admin approves; nothing
 * changes until then.
 */
export default function CoursesPage() {
  const { user } = useAuth()
  const { t, tError, lang } = useLanguage()
  const qc = useQueryClient()
  const admin = user?.role === 'admin'
  const { data: courses = [] } = useQuery<Course[]>({ queryKey: ['courses'], queryFn: coursesApi.mine })
  const { data: subj } = useQuery<{ subjects: SubjectSummary[]; can_practice: boolean }>({ queryKey: ['subjects'], queryFn: subjectsApi.list })
  const { data: ov } = useQuery<Overview>({ queryKey: ['home-overview'], queryFn: sessionsApi.overview })
  const subjects = subj?.subjects ?? []
  const active = courses.filter((c) => !c.archived)
  const mineIds = useMemo(() => new Set(subjects.filter((s) => s.courses.length > 0).map((s) => s.id)), [subjects])

  const student = user?.role === 'student'
  const { data: plan } = useQuery<ElectivePlan>({ queryKey: ['electives'], queryFn: electivesApi.mine, enabled: student })
  const chosen = useMemo(() => new Map((plan?.choices ?? []).map((c) => [c.subject_id, c.semester])), [plan])
  const { data: reqs } = useQuery<{ pending: number }>({ queryKey: ['elective-requests', 'pending'], queryFn: () => electivesApi.adminList('pending'), enabled: admin })

  const [mode, setMode] = useState<Mode | null>(null)
  const current: Mode = mode ?? (mineIds.size || chosen.size ? 'mine' : 'tasks')
  const [q, setQ] = useState('')
  const [picker, setPicker] = useState<string | null>(null)      // semester to add an elective to
  const [change, setChange] = useState<Change | null>(null)      // the request about to be sent
  const [newSubject, setNewSubject] = useState(false)
  const [dragging, setDragging] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const semOf = (s: SubjectSummary) => (student && s.elective ? chosen.get(s.id) ?? null : s.semester)
  const match = (s: SubjectSummary) => !q.trim() || `${s.name} ${s.name_en} ${s.code} ${s.finki_code ?? ''}`.toLowerCase().includes(q.trim().toLowerCase())
  const inMode = (s: SubjectSummary, m: Mode) => m === 'all' ? true : m === 'mine' ? mineIds.has(s.id) || chosen.has(s.id) : m === 'tasks' ? s.tasks > 0
    : m === 'elective' ? s.elective : String(semOf(s)) === m
  const shown = subjects.filter((s) => inMode(s, current) && match(s))
  const semView = SEMS.includes(current)
  const mandatory = semView ? shown.filter((s) => !s.elective) : shown
  const electives = semView ? shown.filter((s) => s.elective) : []
  const name = (id: string) => subjects.find((x) => x.id === id)?.name ?? ''

  const refresh = (p?: ElectivePlan) => {
    if (p) qc.setQueryData(['electives'], p); else qc.invalidateQueries({ queryKey: ['electives'] })
    qc.invalidateQueries({ queryKey: ['subjects'] })
  }
  const fail = (er: any) => setMsg({ ok: false, text: tError(er.response?.data?.detail, 'subjForm.failed') })
  const pendingFor = (id: string) => (plan?.pending_requests ?? []).find((r) => r.add?.subject_id === id || r.remove?.subject_id === id)
  const busy = (id: string) => { if (pendingFor(id)) { setMsg({ ok: false, text: t('el.alreadyWaiting', { name: name(id) }) }); return true } return false }

  /** Put an elective into one of my semesters (or move it there): a request to the admin. */
  const addTo = (id: string, semester: number) => {
    setMsg(null)
    if (!student || busy(id)) return
    const was = chosen.get(id)
    if (was === semester) return
    setChange(was != null ? { remove: id, add: id, semester } : { add: id, semester })
  }
  const removeChoice = (id: string) => {
    setMsg(null)
    if (!busy(id)) setChange({ remove: id })
  }
  const cancelRequest = async (id: string) => {
    try { await electivesApi.cancel(id); refresh() } catch (er) { fail(er) }
  }

  const roleLabel = user ? t(`role.${user.role}` as any) : ''
  const firstName = user?.name?.split(' ')[0] ?? ''
  const staffCourses = active.filter((c) => c.my_role !== 'student')

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* ---- access card + console ---- */}
        <section className="grid lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] gap-5 items-stretch">
          <AccessCard className="w-full max-w-[26rem] home-rise" name={user?.name ?? ''} role={roleLabel} avatarUrl={user?.avatar_url}
            serial={`№ ${(user?.id ?? '').slice(0, 8).toUpperCase()}`}
            lines={[admin ? t('home.accessAll') : t('home.accessCourses', { n: active.length })]} />

          <div className="card-stamp p-5 sm:p-6 flex flex-col min-w-0" data-tour="home-console">
            <p className="font-mono text-[12px] text-ink-muted">ale@finki ~</p>
            <h1 className="mt-1 text-[26px] sm:text-[30px] font-extrabold tracking-tight leading-tight">{t('home.hello', { name: firstName })}</h1>
            <ul className="mt-4 space-y-2 font-mono text-[13.5px]">
              {user?.role === 'student' && (ov?.continue ? (
                <ConsoleLine i={0} label={t('home.continue')}>
                  <Link to={`/tasks/${ov.continue.task_id}`} className="font-sans font-bold text-[15px] hover:text-cobalt inline-flex items-center gap-1.5">
                    {ov.continue.title} <ArrowRight size={15} />
                  </Link>
                  <span className="ml-2 text-ink-muted">{t('home.stepOf', { n: ov.continue.completed_steps, total: Math.max(ov.continue.total_steps, ov.continue.completed_steps) })}</span>
                </ConsoleLine>
              ) : (
                <ConsoleLine i={0} label={t('home.start')}><span className="font-sans">{t('home.startHint')}</span></ConsoleLine>
              ))}
              {user?.role === 'student' && (
                <ConsoleLine i={1} label={t('home.progress')}>
                  <span className="font-sans">{t('home.progressText', { done: ov?.completed ?? 0, going: ov?.in_progress ?? 0 })}</span>
                </ConsoleLine>
              )}
              {staffCourses.length > 0 && (
                <ConsoleLine i={0} label={t('home.yourCourses')}>
                  <span className="font-sans">{t('home.staffCourses', { n: staffCourses.length, students: staffCourses.reduce((a, c) => a + c.students, 0) })}</span>
                </ConsoleLine>
              )}
              {admin && (
                <ConsoleLine i={1} label={t('home.manage')}>
                  <span className="font-sans flex flex-wrap gap-x-3 gap-y-1">
                    <Link to="/admin/courses" className="font-semibold hover:text-cobalt">{t('adminNav.courses')}</Link>
                    <Link to="/admin/users" className="font-semibold hover:text-cobalt">{t('adminNav.users')}</Link>
                    <Link to="/admin/tasks" className="font-semibold hover:text-cobalt">{t('nav.taskBank')}</Link>
                    <Link to="/admin/ai" className="font-semibold hover:text-cobalt">{t('adminNav.ai')}</Link>
                  </span>
                </ConsoleLine>
              )}
              {admin && (reqs?.pending ?? 0) > 0 && (
                <ConsoleLine i={2} label={t('el.requestsLine')}>
                  <Link to="/admin/electives" className="font-sans font-bold hover:text-cobalt inline-flex items-center gap-1.5">
                    {t('el.requestsWaiting', { n: reqs!.pending })} <ArrowRight size={15} />
                  </Link>
                </ConsoleLine>
              )}
              <ConsoleLine i={2} label={t('home.catalog')}>
                <span className="font-sans">{t('home.catalogText', { n: subjects.length, tasks: subjects.reduce((a, s) => a + s.tasks, 0) })}</span>
              </ConsoleLine>
            </ul>
            {!admin && active.length === 0 && <p className="mt-auto pt-4 text-[13px] text-ink-muted">{t('home.noCourses')}</p>}
          </div>
        </section>

        {/* ---- my courses (put in them by the admin) ---- */}
        {!admin && active.length > 0 && (
          <section className="mt-8" aria-labelledby="my-courses">
            <h2 id="my-courses" className="text-[13px] font-bold text-ink-muted mb-2">{t('home.myCourses')}</h2>
            <ul className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
              {[...active].sort((a, b) => (a.next_due ?? '9').localeCompare(b.next_due ?? '9')).map((c) => <CourseChip key={c.id} c={c} />)}
            </ul>
          </section>
        )}

        {/* ---- the catalogue along the semesters ---- */}
        <section className="mt-10" aria-labelledby="subj-title" data-tour="subjects">
          <div className="flex flex-wrap items-end gap-3">
            <div className="mr-auto">
              <h2 id="subj-title" className="text-[28px] font-extrabold tracking-tight leading-tight">{t('subj.catalog')}</h2>
              <p className="mt-1 text-sm text-ink-muted max-w-xl">{subj?.can_practice ? t('subj.catalogHintAi') : t('subj.catalogHint')}</p>
            </div>
            <label className="relative w-full sm:w-72">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input className="input pl-9 h-10" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('home.search')} aria-label={t('home.search')} />
            </label>
            {admin && <button className="btn-secondary h-10" onClick={() => setNewSubject(true)}><Plus size={15} /> {t('subjForm.new')}</button>}
          </div>

          {student && plan && <PlanBar />}

          {/* the studies as a track: eight stations; a station filters the catalogue (and takes a dragged elective) */}
          <div className="mt-4 card p-4 sm:p-5">
            <div className="flex flex-wrap gap-1.5 mb-4" role="group" aria-label={t('subj.semesterFilter')}>
              {(['mine', 'tasks', 'all', 'elective'] as Mode[]).filter((m) => m !== 'mine' || mineIds.size || chosen.size).map((m) => (
                <button key={m} onClick={() => setMode(m)} aria-pressed={current === m}
                  className={`h-8 px-3 rounded-full text-[13px] font-semibold border-[1.5px] ${current === m ? 'bg-ink text-white border-ink' : 'bg-surface border-line-strong text-ink-soft hover:border-ink'}`}>
                  {t(`home.mode.${m}` as any)} <span className="opacity-60 tabular-nums">{subjects.filter((s) => inMode(s, m)).length}</span>
                </button>
              ))}
            </div>
            <ol className="relative grid grid-cols-4 sm:grid-cols-8 gap-y-4" aria-label={t('home.track')}>
              <span aria-hidden className="hidden sm:block absolute left-[6.25%] right-[6.25%] top-[19px] h-[3px] bg-ink/15 rounded" />
              {SEMS.map((n) => {
                const list = subjects.filter((s) => String(semOf(s)) === n)
                const tasks = list.reduce((a, s) => a + s.tasks, 0)
                const done = list.reduce((a, s) => a + s.done, 0)
                const mineHere = student ? list.filter((s) => s.elective).length : 0
                const on = current === n
                return (
                  <li key={n} className="relative flex flex-col items-center text-center rounded-xl"
                    onDragEnter={(e) => { if (dragging) e.preventDefault() }}
                    onDragOver={(e) => { if (dragging) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; e.currentTarget.dataset.over = '1' } }}
                    onDragLeave={(e) => { delete e.currentTarget.dataset.over }}
                    onDrop={(e) => {
                      e.preventDefault(); delete e.currentTarget.dataset.over
                      const id = dragging || e.dataTransfer.getData('text/x-ale-subject')
                      setDragging(null)
                      if (id) addTo(id, Number(n))
                    }}>
                    <button onClick={() => setMode(n)} aria-pressed={on}
                      className={`relative z-10 w-10 h-10 rounded-full border-[3px] font-extrabold text-[15px] transition-colors
                        ${on ? 'bg-marker border-ink text-ink shadow-stamp-sm' : 'bg-surface border-ink/25 text-ink-soft hover:border-ink'}
                        ${dragging ? 'ring-4 ring-marker/50' : ''}`}>{n}</button>
                    <span className="mt-1.5 text-[12px] font-semibold text-ink-soft">{t('subj.semShort', { n })}</span>
                    <span className="text-[11px] text-ink-muted tabular-nums">{t('home.semCount', { n: list.length })}</span>
                    {mineHere > 0 && <span className="text-[10.5px] font-bold text-ink bg-marker/60 rounded-full px-1.5 mt-0.5">{t('el.mineShort', { n: mineHere })}</span>}
                    {student && tasks > 0 && (
                      <span className="mt-1 h-1.5 w-12 rounded-full bg-line-soft overflow-hidden" title={`${done}/${tasks}`}>
                        <span className="block h-full bg-ink" style={{ width: `${Math.round((done / tasks) * 100)}%` }} />
                      </span>
                    )}
                  </li>
                )
              })}
            </ol>
            {student && <p className="mt-4 text-[12px] text-ink-muted">{t('el.dragHintRequest')}</p>}
            {msg && <p role="status" className={`mt-2 text-[13px] font-semibold ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
          </div>

          {semView && <SemesterHeading n={current} count={mandatory.length} electives={electives.length} onAdd={student ? () => setPicker(current) : undefined} />}

          {shown.length === 0 && !(semView && student) ? (
            <p className="mt-6 card px-5 py-8 text-center text-ink-muted">{q ? t('home.nothingFound') : t('subj.noneInSemester')}</p>
          ) : (
            <>
              <ul className="mt-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {mandatory.map((x) => <li key={x.id}><SubjectCard s={x} /></li>)}
              </ul>
              {semView && (electives.length > 0 || student) && (
                <>
                  <h3 className="mt-8 flex items-center gap-2 font-extrabold text-lg">
                    <span className="rounded-full bg-marker px-2.5 py-0.5 text-[13px] font-bold">{t(student ? 'el.myElectives' : 'subj.electives')}</span>
                    {t('home.electivesIn', { n: current })}
                  </h3>
                  {electives.length === 0 ? (
                    <button onClick={() => setPicker(current)} className="mt-3 w-full rounded-xl border-2 border-dashed border-line-strong px-5 py-6 text-[14px] text-ink-muted hover:border-ink hover:text-ink">
                      <Plus size={15} className="inline -mt-0.5" /> {t('home.addElective', { n: current })}
                    </button>
                  ) : (
                    <ul className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {electives.map((x) => <li key={x.id}><SubjectCard s={x} /></li>)}
                    </ul>
                  )}
                </>
              )}
            </>
          )}
        </section>
      </main>

      {dragging && <DropBar />}
      {newSubject && <SubjectForm subject={null} onClose={() => setNewSubject(false)} />}
      {picker && <ElectivePicker semester={picker} subjects={subjects} taken={chosen}
        onPick={(id) => { setPicker(null); addTo(id, Number(picker)) }} onClose={() => setPicker(null)} />}
      {change && <RequestDialog change={change} name={name} from={change.remove ? chosen.get(change.remove) : undefined}
        onDone={(p) => { setChange(null); refresh(p); setMsg({ ok: true, text: t('el.requestSent') }) }} onClose={() => setChange(null)} />}
    </div>
  )

  /** While a card is dragged: the eight semesters fixed at the bottom of the screen, so they can be reached wherever
   *  the card was (the track at the top may be far up the page). */
  function DropBar() {
    return (
      <div className="fixed inset-x-0 bottom-0 z-40 p-3 sm:p-4 pointer-events-none">
        <div className="max-w-3xl mx-auto rounded-2xl bg-ink text-white shadow-2xl p-3 pointer-events-auto">
          <p className="text-[12.5px] text-white/70 text-center mb-2">{t('el.dropHere', { name: name(dragging!) })}</p>
          <ol className="grid grid-cols-8 gap-1.5">
            {SEMS.map((n) => (
              <li key={n} className="rounded-xl border-2 border-white/25 h-14 flex flex-col items-center justify-center font-extrabold text-lg transition-colors data-[over]:bg-marker data-[over]:text-ink data-[over]:border-marker"
                onDragEnter={(e) => e.preventDefault()}
                onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; e.currentTarget.dataset.over = '1' }}
                onDragLeave={(e) => { delete e.currentTarget.dataset.over }}
                onDrop={(e) => {
                  e.preventDefault()
                  const id = dragging || e.dataTransfer.getData('text/x-ale-subject')
                  setDragging(null)
                  if (id) addTo(id, Number(n))
                }}>
                {n}
              </li>
            ))}
          </ol>
        </div>
      </div>
    )
  }

  function PlanBar() {
    const p = plan!
    const pend = p.pending_requests ?? []
    const last = p.requests.find((r) => r.status === 'approved' || r.status === 'rejected')
    return (
      <div className="mt-6 rounded-xl border-2 border-line bg-surface px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="inline-flex items-center gap-2 font-bold text-[14px]"><Sparkles size={15} /> {t('el.mineTitle', { n: p.choices.length })}</span>
        <span className="text-[13px] text-ink-muted flex-1 min-w-[14rem]">{t('el.requestHint')}</span>
        {pend.length > 0 && (
          <ul className="basis-full rounded-lg bg-ink text-white px-3 py-2 text-[13px] divide-y divide-white/10">
            <li className="pb-1.5 font-bold text-marker">{t('el.pendingN', { n: pend.length })}</li>
            {pend.map((r) => (
              <li key={r.id} className="py-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span>{describe(r)}</span>
                <button className="ml-auto text-[12.5px] underline text-white/80 hover:text-white" onClick={() => cancelRequest(r.id)}>{t('el.cancelRequest')}</button>
              </li>
            ))}
          </ul>
        )}
        {last && last.decided_at && (
          <p className={`basis-full text-[12.5px] ${last.status === 'approved' ? 'text-ok' : 'text-bad'}`}>
            {t(last.status === 'approved' ? 'el.lastApprovedX' : 'el.lastRejectedX', { what: describe(last) })}
            {last.admin_note && <> — „{last.admin_note}“</>}
          </p>
        )}
      </div>
    )
  }

  function describe(r: ElectiveRequest) {
    return describeRequest(r, t)
  }

  function SubjectCard({ s }: { s: SubjectSummary }) {
    const pct = s.tasks ? Math.round((s.done / s.tasks) * 100) : 0
    const canDrag = student && s.elective
    const mineSem = chosen.get(s.id)
    return (
      <div className={`group relative h-full ${canDrag ? 'cursor-grab active:cursor-grabbing' : ''}`} draggable={canDrag}
        onDragStart={(e) => {
          if (!canDrag) return
          e.dataTransfer.setData('text/x-ale-subject', s.id)   // Firefox starts a drag only with data set
          e.dataTransfer.setData('text/plain', s.name)
          e.dataTransfer.effectAllowed = 'move'
          setTimeout(() => setDragging(s.id), 0)   // after the browser took its drag image (changing the DOM now can cancel it)
        }} onDragEnd={() => setDragging(null)}>
        <Link to={`/subjects/${s.id}`} draggable={false}
          className={`card p-4 h-full flex flex-col border-2 hover:border-ink transition-colors ${mineSem ? 'border-ink' : ''}`}>
          <div className="flex items-start gap-3">
            <SubjectIcon icon={s.icon} color={s.color} size={40} />
            <div className={`min-w-0 flex-1 ${canDrag ? 'pr-16' : ''}`}>
              <p className="flex flex-wrap items-center gap-x-1.5 text-[11px] font-bold text-ink-muted">
                <span className="font-mono text-ink-soft">{s.finki_code || s.code}</span>
                {s.semester && <span>· {t(s.elective ? 'el.recommended' : 'subj.semShort', { n: s.semester })}</span>}
                {s.elective && <span className="rounded-full bg-marker/40 text-ink px-1.5">{t('subj.elective')}</span>}
              </p>
              <h3 className="mt-0.5 font-bold text-[15px] leading-snug group-hover:text-cobalt">{s.name}</h3>
              {mineSem && <p className="mt-1 text-[11.5px] font-bold text-ink">{t('el.inMySem', { n: mineSem })}</p>}
            </div>
          </div>
          <div className="mt-auto pt-3 flex items-center gap-2 text-[12px] text-ink-muted">
            {s.languages.slice(0, 5).map((l) => <span key={l} className={`${langClass(l)} w-2 h-2 rounded-full bg-marker ring-1 ring-black/10`} title={l} />)}
            {s.courses.length > 0 && <span className="inline-flex items-center gap-1 font-semibold text-ink-soft"><GraduationCap size={12} /> {s.courses.map((c) => c.code).join(', ')}</span>}
            <span className="ml-auto tabular-nums">{s.tasks ? t('subj.progress', { done: s.done, total: s.tasks }) : t('subj.noTasksShort')}</span>
            {s.generated > 0 && <span className="inline-flex items-center gap-0.5"><Sparkles size={11} /> {s.generated}</span>}
          </div>
          {s.tasks > 0 && student && (
            <div className="mt-2 h-1.5 rounded-full bg-line-soft overflow-hidden"><div className="h-full bg-ink" style={{ width: `${pct}%` }} /></div>
          )}
        </Link>
        {canDrag && (
          <div className="absolute top-3 right-3 flex items-center gap-1">
            <label className="text-[11px] font-semibold text-ink-muted bg-surface/90 rounded-md" title={t('el.semesterOfMine')}>
              <span className="sr-only">{t('el.semesterOfMine')}</span>
              <select className="h-7 rounded-md border border-line-strong bg-surface px-1 text-[12px] font-bold text-ink"
                value={mineSem ?? ''} onChange={(e) => e.target.value && addTo(s.id, Number(e.target.value))}>
                <option value="">{t('el.addShort')}</option>
                {SEMS.map((n) => <option key={n} value={n}>{n}.</option>)}
              </select>
            </label>
            {mineSem && (
              <button className="h-7 w-7 inline-flex items-center justify-center rounded-md border border-line-strong bg-surface text-ink-muted hover:text-bad hover:border-bad"
                onClick={() => removeChoice(s.id)} aria-label={t('el.removeFrom', { name: s.name })} title={t('el.removeFrom', { name: s.name })}><X size={14} /></button>
            )}
          </div>
        )}
      </div>
    )
  }

  function CourseChip({ c }: { c: Course }) {
    const staff = c.my_role !== 'student'
    return (
      <li className="snap-start shrink-0 w-64">
        <Link to={`/courses/${c.id}`} className="group card p-4 h-full flex flex-col border-2 hover:border-ink transition-colors">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-bold bg-ink text-white rounded px-1.5 py-0.5 truncate max-w-[9rem]">{c.code}</span>
            <span className="ml-auto text-[11px] font-semibold text-ink-muted">{staff ? permLabel(c.template, t, c.permissions) : t('courseRole.student')}</span>
          </div>
          <p className="mt-2 font-bold leading-snug group-hover:text-cobalt line-clamp-2">{c.name}</p>
          <p className="mt-auto pt-2 text-[12.5px] text-ink-muted flex items-center gap-1.5">
            {staff ? <><Users size={13} /> {c.students === 1 ? t('courses.studentOne') : t('courses.studentsN', { n: c.students })}</>
              : c.next_due ? <span title={formatDateTime(c.next_due, lang)} className="inline-flex items-center gap-1.5"><CalendarClock size={13} /> {t('courses.nextDue', { when: relative(c.next_due, lang) })}</span>
              : t('courses.noDeadlines')}
            <ChevronRight size={14} className="ml-auto text-ink-faint group-hover:text-cobalt" />
          </p>
        </Link>
      </li>
    )
  }

  function SemesterHeading({ n, count, electives, onAdd }: { n: string; count: number; electives: number; onAdd?: () => void }) {
    return (
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <h3 className="text-xl font-extrabold">{t('subj.semester', { n })}</h3>
        <span className="text-[13px] text-ink-muted">{t('home.semSummary', { m: count, e: electives })}</span>
        {onAdd && <button className="btn-secondary btn-sm ml-auto" onClick={onAdd}><Plus size={14} /> {t('home.addElective', { n })}</button>}
      </div>
    )
  }
}

function ConsoleLine({ i, label, children }: { i: number; label: string; children: React.ReactNode }) {
  return (
    <li className="console-line flex flex-wrap items-baseline gap-x-2 gap-y-1" style={{ animationDelay: `${150 + i * 180}ms` }}>
      <span className="text-ink-muted shrink-0">{label} ›</span>
      <span className="min-w-0">{children}</span>
    </li>
  )
}

type Change = { remove?: string; add?: string; semester?: number }

/** A student: put an elective in this semester of mine (or move one of mine here). */
function ElectivePicker({ semester, subjects, taken, onPick, onClose }: { semester: string; subjects: SubjectSummary[]; taken: Map<string, number>; onPick: (id: string) => void; onClose: () => void }) {
  const { t } = useLanguage()
  const [q, setQ] = useState('')
  const list = subjects.filter((s) => s.elective && taken.get(s.id) !== Number(semester) &&
    (!q.trim() || `${s.name} ${s.finki_code ?? ''}`.toLowerCase().includes(q.trim().toLowerCase())))
    .sort((a, b) => Number(String(b.semester) === semester) - Number(String(a.semester) === semester))
  return (
    <Modal title={t('home.addElective', { n: semester })} onClose={onClose}>
      <label className="relative mt-3 block">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
        <input autoFocus className="input pl-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('home.search')} aria-label={t('home.search')} />
      </label>
      <ul className="mt-3 overflow-y-auto divide-y divide-line-soft">
        {list.map((s) => <SubjectPick key={s.id} s={s} note={taken.has(s.id) ? t('el.inMySem', { n: taken.get(s.id)! }) : undefined} onClick={() => onPick(s.id)} />)}
        {list.length === 0 && <li className="px-2 py-6 text-center text-ink-muted text-sm">{t('home.nothingFound')}</li>}
      </ul>
    </Modal>
  )
}

/** What a request asks for, in a few words: "Add: X (sem. 5)", "Take out: X", "Move: X → sem. 6", "X → Y". */
export function describeRequest(r: ElectiveRequest, t: ReturnType<typeof useLanguage>['t']) {
  const sem = (n?: number | null) => (n ? t('subj.semShort', { n }) : '')
  if (r.add && r.remove && r.add.subject_id === r.remove.subject_id) return t('el.reqMove', { name: r.add.name, from: sem(r.remove.semester), to: sem(r.add.semester) })
  if (r.add && r.remove) return t('el.reqSwap', { out: r.remove.name, in: r.add.name, sem: sem(r.add.semester) })
  if (r.add) return t('el.reqAdd', { name: r.add.name, sem: sem(r.add.semester) })
  return t('el.reqRemove', { name: r.remove?.name ?? '', sem: sem(r.remove?.semester) })
}

/** A change of my electives is a request to the admin: what it asks for, an optional reason, "Send the request" or
 *  "Cancel". */
function RequestDialog({ change, name, from, onDone, onClose }: {
  change: Change; name: (id: string) => string; from?: number; onDone: (p: ElectivePlan) => void; onClose: () => void
}) {
  const { t, tError } = useLanguage()
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const id = (change.add ?? change.remove)!
  const what = change.add && change.remove ? t('el.reqMove', { name: name(id), from: t('subj.semShort', { n: from ?? 0 }), to: t('subj.semShort', { n: change.semester! }) })
    : change.add ? t('el.reqAdd', { name: name(id), sem: t('subj.semShort', { n: change.semester! }) })
    : t('el.reqRemove', { name: name(id), sem: from ? t('subj.semShort', { n: from }) : '' })
  const send = async () => {
    setBusy(true); setErr('')
    try {
      onDone(change.add ? await electivesApi.choose(change.add, change.semester!, reason) : await electivesApi.drop(change.remove!, reason))
    } catch (er: any) { setErr(tError(er.response?.data?.detail, 'subjForm.failed')); setBusy(false) }
  }
  return (
    <Modal title={t('el.requestTitle')} onClose={onClose}>
      <p className="mt-3 rounded-lg bg-marker-soft/60 border border-ink/10 px-3 py-2.5 font-semibold text-[14px]">{what}</p>
      <p className="mt-2 text-[13px] text-ink-muted">{t('el.requestExplain')}</p>
      <label className="mt-3 block">
        <span className="field-label">{t('el.reasonOptional')}</span>
        <textarea className="input min-h-[4.5rem]" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={1000} />
      </label>
      {err && <p role="alert" className="mt-2 text-[13px] text-bad">{err}</p>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-secondary" onClick={onClose}>{t('el.giveUp')}</button>
        <button className="btn-primary" disabled={busy} onClick={send}>{busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />} {t('el.sendRequest')}</button>
      </div>
    </Modal>
  )
}

function SubjectPick({ s, note, onClick }: { s: SubjectSummary; note?: string; onClick: () => void }) {
  const { t } = useLanguage()
  return (
    <li>
      <button className="w-full text-left flex items-center gap-3 px-2 py-2 hover:bg-paper rounded-lg" onClick={onClick}>
        <SubjectIcon icon={s.icon} color={s.color} size={28} />
        <span className="min-w-0 flex-1"><span className="block font-semibold text-[13.5px] truncate">{s.name}</span>
          <span className="text-[12px] text-ink-muted font-mono">{s.finki_code || s.code}{s.semester ? ` · ${t('el.recommended', { n: s.semester })}` : ''}{note ? ` · ${note}` : ''}</span></span>
        <Plus size={15} className="text-ink-faint" />
      </button>
    </li>
  )
}

function Modal({ title, onClose, wide = false, children }: { title: string; onClose: () => void; wide?: boolean; children: React.ReactNode }) {
  const { t } = useLanguage()
  return (
    <div className="fixed inset-0 z-50 bg-ink/50 flex items-start sm:items-center justify-center p-4 overflow-y-auto" role="dialog" aria-modal="true" aria-label={title}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}>
      <div className={`card-stamp w-full ${wide ? 'max-w-3xl' : 'max-w-lg'} p-5 max-h-[90vh] flex flex-col overflow-y-auto`}>
        <div className="flex items-center gap-2">
          <h2 className="font-extrabold text-lg flex-1">{title}</h2>
          <button className="btn-ghost btn-sm px-1.5" onClick={onClose} aria-label={t('form.cancel')}><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>
  )
}
