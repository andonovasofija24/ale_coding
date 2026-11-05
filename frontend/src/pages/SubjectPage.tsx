import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, BookOpen, CheckCircle2, ChevronRight, CircleDot, ExternalLink, GraduationCap, KeyRound, Loader2, Sparkles, Users, Wand2, X } from 'lucide-react'
import { subjectsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { PracticeWork, StudentPractice, SubjectDetail, SubjectTask } from '../types'
import AppHeader from '../components/AppHeader'
import SubjectIcon from '../components/SubjectIcon'
import TaskRows from '../components/TaskRows'
import { langClass, langInfo } from '../lib/languages'
import EmptyState, { IconTile } from '../components/EmptyState'

/** One subject: its practice tasks (by language), my courses of it, and practice with AI (on my own key). */
export default function SubjectPage() {
  const { subjectId } = useParams<{ subjectId: string }>()
  const { t } = useLanguage()
  const qc = useQueryClient()
  const { data: s, isLoading } = useQuery<SubjectDetail>({ queryKey: ['subject', subjectId], queryFn: () => subjectsApi.get(subjectId!) })
  const [filter, setFilter] = useState('all')

  if (isLoading || !s) {
    return <Shell><div className="flex justify-center py-20 text-ink-muted"><Loader2 className="animate-spin" /></div></Shell>
  }
  const langs = [...new Set(s.tasks.map((x) => x.language))]
  const shown = filter === 'all' ? s.tasks : s.tasks.filter((x) => x.language === filter)
  const done = s.tasks.filter((x) => x.status === 'completed').length
  const remove = async (task: SubjectTask) => {
    if (!confirm(t('subj.deleteConfirm', { title: task.title }))) return
    await subjectsApi.deletePractice(task.id)
    qc.invalidateQueries({ queryKey: ['subject', subjectId] })
    qc.invalidateQueries({ queryKey: ['subjects'] })
  }

  return (
    <Shell>
      <Link to="/courses" className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
        <ArrowLeft size={15} /> {t('subj.all')}
      </Link>

      {/* hero in the subject's colour */}
      <header className="mt-3 relative overflow-hidden rounded-2xl border-2 border-ink/90 shadow-[4px_4px_0_rgba(26,34,51,.9)]" style={{ background: s.color }}>
        <div className="absolute inset-0 opacity-[.13]" aria-hidden
          style={{ backgroundImage: 'repeating-linear-gradient(135deg, #fff 0 2px, transparent 2px 14px)' }} />
        <div className="relative px-6 py-7 sm:px-8 flex flex-wrap items-center gap-5 text-white">
          <span className="rounded-2xl bg-white/15 p-2 ring-2 ring-white/30"><SubjectIcon icon={s.icon} color="transparent" size={56} /></span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-[12px] font-bold">
              <span className="font-mono rounded bg-white text-ink px-1.5 py-0.5">{s.code}</span>
              {s.semester && <span className="rounded-full bg-black/20 px-2 py-0.5">{t('subj.semester', { n: s.semester })}</span>}
              {s.elective && <span className="rounded-full bg-black/20 px-2 py-0.5">{t('subj.elective')}</span>}
            </div>
            <h1 className="mt-2 text-[28px] sm:text-[32px] font-extrabold tracking-tight leading-tight">{s.name}</h1>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {s.languages.map((l) => (
                <span key={l} className={`${langClass(l)} text-[12px] font-bold rounded-full px-2.5 py-0.5 bg-marker text-ink border border-black/10`}>{langInfo(l).label}</span>
              ))}
            </div>
          </div>
          <div className="text-right">
            <p className="text-[34px] font-extrabold leading-none tabular-nums">{done}<span className="text-white/60 text-xl">/{s.tasks.length}</span></p>
            <p className="text-[12px] text-white/80 mt-1">{t('subj.solved')}</p>
          </div>
        </div>
      </header>

      <div className="mt-6 grid lg:grid-cols-[minmax(0,1fr)_21rem] gap-6 items-start">
        {/* tasks */}
        <section>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-extrabold text-lg flex items-center gap-2.5 mr-auto"><IconTile size="sm"><BookOpen size={15} /></IconTile> {t('subj.tasks')}</h2>
            {langs.length > 1 && ['all', ...langs].map((l) => (
              <button key={l} onClick={() => setFilter(l)} aria-pressed={filter === l}
                className={`${l === 'all' ? '' : langClass(l)} h-7 px-2.5 rounded-full border text-[12.5px] font-semibold flex items-center gap-1.5 ${
                  filter === l ? 'bg-ink border-ink text-white' : 'bg-surface border-line text-ink-muted hover:text-ink'}`}>
                {l !== 'all' && <span className="w-2 h-2 rounded-full bg-marker" />}
                {l === 'all' ? t('tasks.filterAll') : langInfo(l).label}
              </button>
            ))}
          </div>
          <div className="mt-3">
            {s.tasks.length === 0 ? (
              <EmptyState icon={<BookOpen size={24} />} tone="cobalt" title={t('subj.noTasks')} text={s.can_practice ? t('subj.noTasksAi') : t('subj.noTasksHint')} />
            ) : <TaskRows tasks={shown} />}
          </div>

          {s.staff && <StudentPracticeSection subjectId={s.id} />}

          {s.generated.length > 0 && (
            <div className="mt-8">
              <h2 className="font-extrabold text-lg flex items-center gap-2.5"><IconTile size="sm" tone="marker"><Sparkles size={15} /></IconTile> {t('subj.myAi')}</h2>
              <p className="text-[13px] text-ink-muted mt-0.5">{t('subj.myAiHint')}</p>
              <div className="mt-3"><TaskRows tasks={s.generated} numbered={false} onDelete={remove} /></div>
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <PracticeCard s={s} />
          <section className="card p-4">
            <h2 className="font-bold flex items-center gap-2.5"><IconTile size="sm" tone="ok"><GraduationCap size={15} /></IconTile> {t('subj.myCourses')}</h2>
            {s.courses.length === 0 ? <p className="mt-1.5 text-[13px] text-ink-muted">{t('subj.noCourses')}</p> : (
              <ul className="mt-2 space-y-1.5">
                {s.courses.map((c) => (
                  <li key={c.id}>
                    <Link to={`/courses/${c.id}`} className="group flex items-center gap-2 rounded-lg border border-line px-3 py-2 hover:border-ink-faint">
                      <span className="font-mono text-[11px] font-bold bg-ink text-white rounded px-1.5 py-0.5">{c.code}</span>
                      <span className="min-w-0 flex-1 text-[13.5px] font-semibold truncate group-hover:text-cobalt">{c.semester || c.name}</span>
                      <ChevronRight size={15} className="text-ink-faint" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </Shell>
  )
}

const STAGES = ['subj.genTask', 'subj.genSolution', 'subj.genTests', 'subj.genCheck'] as const

/** "Practise with AI": choose the language, the level and (optionally) a topic; AI writes a whole new task. */
function PracticeCard({ s }: { s: SubjectDetail }) {
  const { t, tError } = useLanguage()
  const navigate = useNavigate()
  const [language, setLanguage] = useState(s.languages[0] ?? '')
  const [level, setLevel] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [topic, setTopic] = useState('')
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState(0)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!busy) return
    setStage(0)
    const id = setInterval(() => setStage((x) => Math.min(x + 1, STAGES.length - 1)), 9000)
    return () => clearInterval(id)
  }, [busy])

  if (!s.can_practice) {
    return (
      <section className="rounded-xl border-2 border-dashed border-marker bg-marker-soft/50 p-4">
        <h2 className="font-bold flex items-center gap-2.5"><IconTile size="sm" tone="marker"><Wand2 size={15} /></IconTile> {t('subj.aiTitle')}</h2>
        <p className="mt-1.5 text-[13px] text-ink-soft">{t('subj.aiNeedsKey')}</p>
        <Link to="/profile" className="btn-secondary btn-sm mt-3"><KeyRound size={14} /> {t('subj.addKey')}</Link>
      </section>
    )
  }
  const go = async () => {
    setBusy(true); setError('')
    try {
      const r = await subjectsApi.practice(s.id, { language, level, topic })
      navigate(`/tasks/${r.task_id}`)
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'subj.genFailed'))
    } finally { setBusy(false) }
  }
  return (
    <section className="rounded-xl border-2 border-ink bg-surface p-4 shadow-[3px_3px_0_rgba(26,34,51,.9)]">
      <h2 className="font-bold flex items-center gap-2.5"><IconTile size="sm" tone="marker"><Wand2 size={15} /></IconTile> {t('subj.aiTitle')}</h2>
      <p className="mt-1 text-[12.5px] text-ink-muted">{t('subj.aiHint')}</p>
      <fieldset className="mt-3" disabled={busy}>
        <legend className="field-label">{t('subj.language')}</legend>
        <div className="flex flex-wrap gap-1.5">
          {s.languages.map((l) => (
            <button key={l} type="button" onClick={() => setLanguage(l)} aria-pressed={language === l}
              className={`${langClass(l)} h-8 px-2.5 rounded-lg border text-[12.5px] font-bold flex items-center gap-1.5 ${
                language === l ? 'bg-marker border-marker-deep/40 text-ink ring-2 ring-marker/40' : 'bg-surface border-line text-ink-muted hover:text-ink'}`}>
              {langInfo(l).label}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="mt-3" disabled={busy}>
        <legend className="field-label">{t('subj.level')}</legend>
        <div className="grid grid-cols-3 rounded-lg border border-line overflow-hidden text-[12.5px] font-semibold">
          {(['easy', 'medium', 'hard'] as const).map((x) => (
            <button key={x} type="button" onClick={() => setLevel(x)} aria-pressed={level === x}
              className={`h-8 ${level === x ? 'bg-ink text-white' : 'bg-surface text-ink-muted hover:text-ink'} ${x !== 'easy' ? 'border-l border-line' : ''}`}>
              {t(`subj.level.${x}` as any)}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="mt-3">
        <label htmlFor="topic" className="field-label">{t('subj.topic')}</label>
        <input id="topic" className="input h-9" value={topic} maxLength={300} disabled={busy} onChange={(e) => setTopic(e.target.value)}
          placeholder={t('subj.topicPh')} />
      </div>
      {error && <p role="alert" className="mt-3 text-[13px] text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}
      <button className="btn-primary w-full mt-4" onClick={go} disabled={busy || !language}>
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {busy ? t(STAGES[stage]) : t('subj.generate')}
      </button>
      {busy && <p className="mt-2 text-[12px] text-ink-muted text-center" aria-live="polite">{t('subj.genWait')}</p>}
    </section>
  )
}

/** Staff of the subject (professor, assistants, лаборанти): what the students practise here with their own AI key. */
function StudentPracticeSection({ subjectId }: { subjectId: string }) {
  const { t } = useLanguage()
  const { data, isLoading } = useQuery<StudentPractice>({ queryKey: ['student-practice', subjectId], queryFn: () => subjectsApi.studentPractice(subjectId) })
  const [open, setOpen] = useState<string | null>(null)
  const [work, setWork] = useState<string | null>(null)
  return (
    <div className="mt-8">
      <h2 className="font-extrabold text-lg flex items-center gap-2.5"><IconTile size="sm" tone="ok"><Users size={15} /></IconTile> {t('sp.title')}</h2>
      <p className="text-[13px] text-ink-muted mt-0.5">{t('sp.hint')}</p>
      {isLoading || !data ? <div className="mt-4 text-ink-muted"><Loader2 className="animate-spin" size={18} /></div>
        : data.students.length === 0 ? <p className="mt-3 card px-4 py-6 text-center text-[13px] text-ink-muted">{t('sp.none')}</p> : (
          <ul className="mt-3 card divide-y divide-line-soft overflow-hidden">
            {data.students.map((st) => (
              <li key={st.user_id}>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-paper/60" aria-expanded={open === st.user_id}
                  onClick={() => setOpen(open === st.user_id ? null : st.user_id)}>
                  <span className="min-w-0 flex-1"><span className="block font-semibold text-[14px] truncate">{st.name}</span>
                    <span className="block text-[12px] text-ink-muted truncate">{st.email}</span></span>
                  <span className="text-[12.5px] tabular-nums text-ink-soft">{t('sp.count', { n: st.tasks.length, done: st.done })}</span>
                  <ChevronRight size={15} className={`text-ink-faint transition-transform ${open === st.user_id ? 'rotate-90' : ''}`} />
                </button>
                {open === st.user_id && (
                  <ul className="px-4 pb-3 space-y-1">
                    {st.tasks.map((x) => (
                      <li key={x.id}>
                        <button className="w-full flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-left hover:border-ink-faint" onClick={() => setWork(x.id)}>
                          {x.status === 'completed' ? <CheckCircle2 size={14} className="text-ok shrink-0" /> : <CircleDot size={14} className={x.status ? 'text-marker-deep shrink-0' : 'text-ink-faint shrink-0'} />}
                          <span className="min-w-0 flex-1 text-[13px] font-medium truncate">{x.title}</span>
                          <span className={`${langClass(x.language)} text-[11px] font-bold rounded-full px-2 bg-marker`}>{langInfo(x.language).label}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      {work && <WorkModal taskId={work} onClose={() => setWork(null)} />}
    </div>
  )
}

function WorkModal({ taskId, onClose }: { taskId: string; onClose: () => void }) {
  const { t } = useLanguage()
  const { data } = useQuery<PracticeWork>({ queryKey: ['practice-work', taskId], queryFn: () => subjectsApi.practiceWork(taskId) })
  return (
    <div className="fixed inset-0 z-50 bg-ink/50 flex items-start sm:items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={data?.title ?? ''}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}>
      <div className="card-stamp w-full max-w-3xl p-5 max-h-[90vh] flex flex-col">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-[12px] text-ink-muted">{data?.student.name} · {data?.student.email}</p>
            <h2 className="font-extrabold text-lg truncate">{data?.title ?? '…'}</h2>
          </div>
          <Link to={`/tasks/${taskId}`} className="btn-ghost btn-sm"><ExternalLink size={14} /> {t('sp.openTask')}</Link>
          <button className="btn-ghost btn-sm px-1.5" onClick={onClose} aria-label={t('form.cancel')}><X size={16} /></button>
        </div>
        {!data ? <div className="py-10 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div> : (
          <div className="mt-3 grid sm:grid-cols-[13rem_minmax(0,1fr)] gap-3 min-h-0 overflow-hidden">
            <ol className="space-y-1 text-[12.5px] overflow-y-auto">
              {data.steps.length === 0 && <li className="text-ink-muted">{t('sp.noSteps')}</li>}
              {data.steps.map((x) => (
                <li key={x.n} className="flex gap-1.5">
                  {x.status === 'completed' ? <CheckCircle2 size={13} className="text-ok mt-0.5 shrink-0" /> : <CircleDot size={13} className="text-ink-faint mt-0.5 shrink-0" />}
                  <span>{x.n}. {x.title}</span>
                </li>
              ))}
            </ol>
            <pre className="rounded-lg bg-ink text-white/90 text-[12.5px] leading-relaxed p-3 overflow-auto font-mono min-h-[12rem]">{data.code || t('sp.noCode')}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">{children}</main>
    </div>
  )
}
