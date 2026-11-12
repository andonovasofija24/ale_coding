import { useEffect, useState } from 'react'
import { canKind } from '../lib/perms'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, ArrowRight, Bot, BotOff, ChevronDown, Clock, Copy, Eye, EyeOff, Flag, GraduationCap, Lightbulb, Loader2,
  Lock, MessageSquareText, Network, Pencil, Play, Timer, TrendingUp, Users, FileText, FolderArchive, ClipboardCheck, TableProperties,
} from 'lucide-react'
import { assignmentsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { Assignment, Feedback } from '../types'
import AppHeader from '../components/AppHeader'
import LangChip from '../components/LangChip'
import Markdown from '../components/Markdown'
import CodeView from '../components/course/CodeView'
import DiagramEditor from '../components/DiagramEditor'
import { diagramKindOf } from '../lib/diagram'
import { FilePreview, ProjectBrowser } from '../components/course/FileViews'

const KIND_ICON = { code: null, document: <FileText size={11} />, project: <FolderArchive size={11} />, offline: <ClipboardCheck size={11} /> }
import { Deadline, KindBadge, Points, StatusBadge, fmt } from '../components/course/bits'
import { countdown, useNow } from '../lib/time'

/** One assignment: rules (deadline, late policy, AI, exam), its tasks, and — for exams — the start / timer / hand-in. */
export default function AssignmentPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const { t } = useLanguage()
  const { data: a, isLoading, isError } = useQuery<Assignment>({
    queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!), enabled: !!assignmentId,
  })

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        {isLoading ? (
          <div className="flex justify-center py-20 text-ink-muted"><Loader2 className="animate-spin" /></div>
        ) : isError || !a ? (
          <p className="py-20 text-center text-ink-muted">{t('assign.notFound')}</p>
        ) : (
          <Content a={a} />
        )}
      </main>
    </div>
  )
}

function Content({ a }: { a: Assignment }) {
  const { t } = useLanguage()
  const staff = a.my_role !== 'student'
  const exam = a.exam && !staff
  const canSubmit = staff || (exam ? a.exam_state === 'running' : a.status === 'open' || a.status === 'late')
  const pointsHidden = !staff && a.scores_after_publish && !a.grades_published
  const showTasks = staff || !exam || a.exam_state !== 'not_started'

  return (
    <>
      <Link to={`/courses/${a.course_id}`} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
        <ArrowLeft size={15} /> {a.course_code} · {a.course_name}
      </Link>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <KindBadge kind={a.kind} />
        <StatusBadge status={a.status} />
        {a.group_name && (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-obj bg-obj-soft rounded-full px-2 py-0.5">
            <Users size={11} /> {a.group_name}
          </span>
        )}
        {staff && canKind(a, a.kind, 'manage') && (
          <Link to={`/assignments/${a.id}/edit`} className="ml-auto btn-secondary btn-sm"><Pencil size={14} /> {t('assign.edit')}</Link>
        )}
      </div>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight">{a.title}</h1>

      <section className="mt-5 card px-5 py-4 grid sm:grid-cols-3 gap-4">
        <div className="sm:col-span-2">
          <p className="text-xs text-ink-muted">{t('assign.deadline')}</p>
          <div className="mt-1"><Deadline a={a} live /></div>
          {!a.exam && (
            <p className="mt-1.5 text-[13px] text-ink-muted flex items-start gap-1.5">
              <Clock size={14} className="shrink-0 mt-0.5" />
              {a.allow_late ? t('assign.lateAllowed', { p: a.late_penalty }) : t('assign.lateNotAllowed')}
            </p>
          )}
        </div>
        <div>
          <p className="text-xs text-ink-muted">{staff ? t('assign.maxPoints') : t('assign.myPoints')}</p>
          <div className="mt-1 text-lg">
            {staff ? <span className="font-bold">{fmt(a.max_points)}</span>
              : pointsHidden ? <span className="text-sm text-ink-muted">{t('exam.pointsLater', { n: fmt(a.max_points) })}</span>
              : <Points got={a.my_score ?? null} max={a.max_points} />}
          </div>
          {staff && a.students_submitted != null && (
            <p className="text-[13px] text-ink-muted">{t('assign.studentsSubmitted', { n: a.students_submitted })}</p>
          )}
        </div>
        <Rules a={a} />
      </section>

      {staff && <StaffTools a={a} />}

      {a.description && (
        <div className="mt-5 task-description"><Markdown>{a.description}</Markdown></div>
      )}

      {exam && <ExamPanel a={a} />}

      {showTasks && (
        <>
          <h2 className="mt-8 panel-title">{t('assign.tasks')}</h2>
          <p className="mt-1 text-[13px] text-ink-muted">{exam && a.exam_state === 'over' ? t('exam.overTasks') : a.ai_mode === 'full' ? t('assign.tasksHint') : t('assign.tasksHintNoAi')}</p>
          <ol className="mt-3 card divide-y divide-line-soft overflow-hidden">
            {a.tasks.map((task, i) => (
              <li key={task.task_id}>
                <Link to={!task.kind || task.kind === 'code' ? `/tasks/${task.task_id}?assignment=${a.id}` : `/assignments/${a.id}/work/${task.task_id}`}
                  className={`group flex items-center gap-4 px-4 sm:px-5 py-4 transition-colors ${canSubmit ? 'hover:bg-paper/60' : 'hover:bg-paper/40'}`}>
                  <span className="w-8 h-8 rounded-lg bg-paper text-sm font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold group-hover:text-cobalt truncate">{task.title}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-ink-muted">
                      {!task.kind || task.kind === 'code' ? <LangChip lang={task.language} />
                        : <span className="inline-flex items-center gap-1 font-semibold text-ink-soft bg-paper border border-line rounded px-1.5 py-px">
                            {KIND_ICON[task.kind]} {t(`kind.${task.kind}` as any)}</span>}
                      {staff && task.variant_group != null && (
                        <span className="font-semibold text-obj bg-obj-soft rounded-full px-2 py-0.5">{t('variant.badge', { n: task.variant_group })}</span>
                      )}
                      {!staff && task.my_submissions ? (task.my_submissions === 1 ? t('assign.submissionOne') : t('assign.submissionsN', { n: task.my_submissions })) : null}
                      {!staff && task.my_late && <span className="text-bad font-semibold">{t('grades.late')}</span>}
                      {!staff && task.more_points && (
                        <span className="inline-flex items-center gap-1 font-semibold text-cobalt bg-cobalt-soft rounded-full px-2 py-0.5" title={t('morePoints.text')}>
                          <TrendingUp size={11} /> {t('morePoints.title')}
                        </span>
                      )}
                    </div>
                  </div>
                  {staff ? <span className="text-sm text-ink-muted tabular-nums">{fmt(task.points)} {t('assign.pointsShort')}</span>
                    : pointsHidden ? <span className="text-sm text-ink-muted tabular-nums">/ {fmt(task.points)}</span>
                    : <Points got={task.my_score ?? null} max={task.points} />}
                  <ArrowRight size={16} className="text-ink-faint group-hover:text-cobalt" />
                </Link>
                {!staff && task.has_feedback && <FeedbackBox assignmentId={a.id} taskId={task.task_id} />}
              </li>
            ))}
          </ol>
        </>
      )}
    </>
  )
}

/** Small chips with the rules that change how students work: AI tutor, exam timer, network, results. */
function Rules({ a }: { a: Assignment }) {
  const { t } = useLanguage()
  const chips: { icon: JSX.Element; text: string; tone?: string }[] = []
  if (a.ai_mode === 'off') chips.push({ icon: <BotOff size={13} />, text: t('ai.off'), tone: 'bg-bad-soft text-bad' })
  else if (a.ai_mode === 'hints') chips.push({ icon: <Lightbulb size={13} />, text: t('ai.hintsN', { n: a.hint_limit }), tone: 'bg-marker-soft text-ink' })
  else chips.push({ icon: <Bot size={13} />, text: t('ai.full') })
  if (a.exam && a.duration_minutes) chips.push({ icon: <Timer size={13} />, text: t('exam.minutes', { n: a.duration_minutes }) })
  if (a.ip_restricted) chips.push({ icon: <Network size={13} />, text: t('exam.ipRestricted') })
  if (a.results_visibility !== 'full') chips.push({ icon: <EyeOff size={13} />, text: t(`results.${a.results_visibility}` as any) })
  if (a.scores_after_publish) chips.push({ icon: <Lock size={13} />, text: a.grades_published ? t('grading.published') : t('exam.pointsAfterPublishShort') })
  return (
    <div className="sm:col-span-3 flex flex-wrap gap-1.5 border-t border-line-soft pt-3">
      {chips.map((c, i) => (
        <span key={i} className={`inline-flex items-center gap-1.5 text-[12px] font-medium rounded-full px-2.5 py-1 ${c.tone ?? 'bg-paper text-ink-soft'}`}>
          {c.icon} {c.text}
        </span>
      ))}
    </div>
  )
}

/** Staff: links to grading and the similarity check, and publishing the grades. */
function StaffTools({ a }: { a: Assignment }) {
  const { t } = useLanguage()
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const toggle = async () => {
    if (!a.grades_published && !confirm(t('grading.publishConfirm'))) return
    setBusy(true)
    try {
      await assignmentsApi.publish(a.id, !a.grades_published)
      qc.invalidateQueries({ queryKey: ['assignment', a.id] })
    } finally { setBusy(false) }
  }
  return (
    <section className="mt-4 flex flex-wrap items-center gap-2">
      <Link to={`/assignments/${a.id}/grading`} className="btn-primary"><GraduationCap size={15} /> {t('grading.open')}</Link>
      <Link to={`/assignments/${a.id}/similarity`} className="btn-secondary"><Copy size={15} /> {t('sim.open')}</Link>
      {canKind(a, a.kind, 'grade') && <Link to={`/assignments/${a.id}/quick`} className="btn-secondary"><TableProperties size={15} /> {t('quick.open')}</Link>}
      {canKind(a, a.kind, 'grade') && (
        <button onClick={toggle} disabled={busy} className={a.grades_published ? 'btn-ghost ml-auto' : 'btn-secondary ml-auto'}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : a.grades_published ? <EyeOff size={15} /> : <Eye size={15} />}
          {a.grades_published ? t('grading.unpublish') : t('grading.publish')}
        </button>
      )}
    </section>
  )
}

/** Student, exam: start (personal timer), time left, hand in early. */
function ExamPanel({ a }: { a: Assignment }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const offset = a.server_time ? new Date(a.server_time).getTime() - Date.now() : 0
  const now = useNow(1000) + offset
  const ends = a.attempt?.ends_at ? new Date(a.attempt.ends_at).getTime() : null
  const left = ends ? countdown(new Date(ends).toISOString(), now) : null
  const timeUp = a.exam_state === 'running' && ends != null && now >= ends
  useEffect(() => { if (timeUp) qc.invalidateQueries({ queryKey: ['assignment', a.id] }) }, [timeUp, qc, a.id])

  const act = async (fn: () => Promise<Assignment>, confirmText?: string) => {
    if (confirmText && !confirm(confirmText)) return
    setBusy(true); setError('')
    try {
      qc.setQueryData(['assignment', a.id], await fn())
      qc.invalidateQueries({ queryKey: ['ai-policy'] })
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'course.actionFailed'))
    } finally { setBusy(false) }
  }

  if (a.exam_state === 'not_started') {
    const blocked = a.ip_ok === false || a.status !== 'open'
    return (
      <section className="mt-6 card p-5 sm:p-6 border-l-4 border-l-cobalt">
        <h2 className="text-lg font-bold flex items-center gap-2"><Timer size={18} /> {t('exam.readyTitle')}</h2>
        <ul className="mt-3 space-y-1.5 text-sm text-ink-soft list-disc pl-5">
          <li>{t('exam.ruleTasks', { n: a.task_count ?? 0 })}</li>
          {a.duration_minutes ? <li>{t('exam.ruleTimer', { n: a.duration_minutes })}</li> : <li>{t('exam.ruleDeadline')}</li>}
          <li>{a.ai_mode === 'off' ? t('exam.ruleAiOff') : a.ai_mode === 'hints' ? t('exam.ruleAiHints', { n: a.hint_limit }) : t('exam.ruleAiFull')}</li>
          <li>{t('exam.ruleSignals')}</li>
        </ul>
        {a.ip_ok === false && <p className="mt-3 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{t('err.Not allowed from this network')}</p>}
        {error && <p role="alert" className="mt-3 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}
        <button onClick={() => act(() => assignmentsApi.start(a.id), t('exam.startConfirm'))} disabled={busy || blocked} className="mt-4 btn-primary btn-lg">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />} {t('exam.start')}
        </button>
      </section>
    )
  }
  if (a.exam_state === 'running') {
    const urgent = ends != null && ends - now < 5 * 60_000
    return (
      <section className={`mt-6 card p-4 sm:p-5 flex flex-wrap items-center gap-4 ${urgent ? 'border-bad' : ''}`}>
        <div role="timer" aria-live="off">
          <p className="text-xs text-ink-muted">{t('exam.timeLeftLabel')}</p>
          <p className={`text-3xl font-extrabold tabular-nums ${urgent ? 'text-bad' : ''}`}>{left ?? '—'}</p>
        </div>
        <p className="text-[13px] text-ink-muted flex-1 min-w-[14rem]">{t('exam.runningHint')}</p>
        {error && <p role="alert" className="w-full text-sm text-bad">{error}</p>}
        <button onClick={() => act(() => assignmentsApi.finish(a.id), t('exam.finishConfirm'))} disabled={busy} className="btn-secondary">
          <Flag size={15} /> {t('exam.finish')}
        </button>
      </section>
    )
  }
  return (
    <section className="mt-6 card p-4 sm:p-5 flex items-center gap-3">
      <Flag size={18} className="text-ink-muted" />
      <p className="text-sm">
        <span className="font-semibold">{t('exam.over')}</span>{' '}
        <span className="text-ink-muted">{a.attempt ? (a.grades_published ? t('exam.overPublished') : t('exam.overWait')) : t('exam.notTaken')}</span>
      </p>
    </section>
  )
}

/** Student, after publishing: points breakdown, the teacher's comment and line comments on the code. */
function FeedbackBox({ assignmentId, taskId }: { assignmentId: string; taskId: string }) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  const { data } = useQuery<Feedback>({
    queryKey: ['feedback', assignmentId, taskId], queryFn: () => assignmentsApi.feedback(assignmentId, taskId), enabled: open,
  })
  return (
    <div className="px-4 sm:px-5 pb-4 -mt-1">
      <button onClick={() => setOpen((o) => !o)} className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-cobalt hover:underline">
        <MessageSquareText size={14} /> {t('feedback.show')} <ChevronDown size={14} className={open ? 'rotate-180' : ''} />
      </button>
      {open && !data && <Loader2 size={16} className="mt-2 animate-spin text-ink-muted" />}
      {open && data && (
        <div className="mt-3 space-y-3">
          <p className="text-[13px] text-ink-soft">
            {data.override != null ? t('feedback.override', { n: fmt(data.override) })
              : t('feedback.breakdown', { auto: data.auto == null ? '—' : fmt(data.auto), adj: (data.adjust >= 0 ? '+' : '') + fmt(data.adjust) })}
            {' → '}<span className="font-bold">{data.final == null ? '—' : fmt(data.final)} / {fmt(data.points)}</span>
          </p>
          {data.comment && (
            <blockquote className="rounded-lg border-l-[3px] border-l-cobalt bg-cobalt-soft px-3.5 py-2.5 text-sm whitespace-pre-wrap">{data.comment}</blockquote>
          )}
          {data.rubric.length > 0 && data.rubric_scores && (
            <table className="w-full text-sm border border-line-soft rounded-lg overflow-hidden">
              <tbody className="divide-y divide-line-soft">
                {data.rubric.map((r) => (
                  <tr key={r.id}>
                    <td className="px-3 py-1.5">{r.title}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums font-semibold">{fmt(data.rubric_scores![r.id] ?? 0)} / {fmt(r.points)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {data.submissions.map((s) => (
            <div key={s.id}>
              {data.kind === 'code' ? (
                <>
                  <p className="text-[12px] text-ink-muted mb-1">
                    {s.best ? t('feedback.bestSubmission') : t('feedback.submission')} · {s.passed}/{s.total} · {fmt(s.score)} {t('assign.pointsShort')}
                  </p>
                  {diagramKindOf(s.code) ? <div className="card overflow-hidden h-[24rem]"><DiagramEditor code={s.code} kind={diagramKindOf(s.code)!} readOnly /></div>
                    : <CodeView code={s.code} comments={s.comments} maxHeight="24rem" />}
                </>
              ) : data.kind === 'project' ? (
                <ProjectBrowser submissionId={s.id} comments={s.comments} />
              ) : (
                <FilePreview submissionId={s.id} fileType={s.file_type} fileName={s.file_name} height="28rem" />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
