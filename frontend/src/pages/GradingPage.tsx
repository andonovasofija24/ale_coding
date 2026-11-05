import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, CheckCircle2, CircleDot, Clipboard, ClipboardCheck, Copy, Download, Eye, EyeOff, FileText, Flag, FolderArchive,
  Loader2, LogOut, MessageSquareText, Plus, Save, Search, SkipForward, Sparkles, Star, TableProperties, TrendingUp,
} from 'lucide-react'
import { adminApi, assignmentsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { Assignment, GradingSuggestion, Overview, Review } from '../types'
import AppHeader from '../components/AppHeader'
import LangChip from '../components/LangChip'
import CodeView from '../components/course/CodeView'
import DiagramEditor from '../components/DiagramEditor'
import { WebSubmissionView } from '../components/WebWorkspace'
import { diagramKindOf } from '../lib/diagram'
import { FilePreview, ProjectBrowser, formatSize } from '../components/course/FileViews'
import { fmt } from '../components/course/bits'
import { formatDateTime } from '../lib/time'

type Student = Overview['students'][number]

/** The task to open for a student: the first submitted one nobody has reviewed yet, else the first submitted one. */
function firstToReview(s: Student) {
  return s.tasks.find((x) => x.submissions > 0 && !x.reviewed) ?? s.tasks.find((x) => x.submissions > 0) ?? s.tasks[0]
}

/** Staff: every student's work on an assignment — status, points, exam signals; "Review" opens the work, the grade
 *  form and line comments; "Save and next" walks through everything not reviewed yet. */
export default function GradingPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const { t } = useLanguage()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState('')
  const [onlyOpen, setOnlyOpen] = useState(false)
  const { data: a } = useQuery<Assignment>({ queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!) })
  const { data: ov, isLoading } = useQuery<Overview>({ queryKey: ['overview', assignmentId], queryFn: () => assignmentsApi.overview(assignmentId!) })
  const sel = params.get('user') && params.get('task') ? { user: params.get('user')!, task: params.get('task')! } : null
  const reviewRef = useRef<HTMLDivElement>(null)
  const [publishing, setPublishing] = useState(false)
  const [allDone, setAllDone] = useState(false)

  const students = useMemo(() => (ov?.students ?? []).filter((s) =>
    (!q || `${s.name} ${s.email} ${s.group ?? ''}`.toLowerCase().includes(q.toLowerCase())) && (!onlyOpen || s.to_review > 0)), [ov, q, onlyOpen])
  const openCount = (ov?.students ?? []).filter((s) => s.to_review > 0).length

  const pick = (user: string, task: string) => {
    setAllDone(false)
    setParams({ user, task }, { replace: true })
    setTimeout(() => reviewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }
  // After saving: the next submitted, not reviewed work — in table order, starting after the current one.
  const next = (fresh: Overview) => {
    const list = fresh.students
    const start = Math.max(0, list.findIndex((s) => s.user_id === sel?.user))
    for (let k = 0; k < list.length; k++) {
      const s = list[(start + k) % list.length]
      const tk = s.tasks.find((x) => x.submissions > 0 && !x.reviewed && !(s.user_id === sel?.user && x.task_id === sel?.task))
      if (tk) return pick(s.user_id, tk.task_id)
    }
    setAllDone(true)
  }
  const publish = async () => {
    if (!a) return
    if (!a.grades_published && !confirm(t('grading.publishConfirm'))) return
    setPublishing(true)
    try {
      await assignmentsApi.publish(a.id, !a.grades_published)
      qc.invalidateQueries({ queryKey: ['assignment', a.id] }); qc.invalidateQueries({ queryKey: ['overview', a.id] })
    } finally { setPublishing(false) }
  }

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <Link to={`/assignments/${assignmentId}`} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {a?.title ?? t('common.loading')}
        </Link>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[16rem]">
            <h1 className="text-3xl font-extrabold tracking-tight">{t('grading.title')}</h1>
            <p className="mt-1 text-sm text-ink-muted max-w-2xl">{t('grading.hint2')}</p>
          </div>
          {a && a.my_role !== 'student' && <Link to={`/assignments/${assignmentId}/quick`} className="btn-secondary"><TableProperties size={15} /> {t('quick.open')}</Link>}
          <Link to={`/assignments/${assignmentId}/similarity`} className="btn-secondary"><Copy size={15} /> {t('sim.open')}</Link>
          {a && a.my_role !== 'student' && (
            <button onClick={publish} disabled={publishing} className={a.grades_published ? 'btn-secondary' : 'btn-primary'}>
              {publishing ? <Loader2 size={15} className="animate-spin" /> : a.grades_published ? <EyeOff size={15} /> : <Eye size={15} />}
              {a.grades_published ? t('grading.unpublish') : t('grading.publish')}
            </button>
          )}
        </div>
        {a && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 text-[13px] rounded-full px-2.5 py-1 font-medium ${a.grades_published ? 'bg-ok-soft text-ok' : 'bg-line-soft text-ink-soft'}`}>
              {a.grades_published ? <Eye size={13} /> : <EyeOff size={13} />} {a.grades_published ? t('grading.publishedState') : t('grading.notPublishedState')}
            </span>
            {ov && (
              <span className={`inline-flex items-center gap-1.5 text-[13px] rounded-full px-2.5 py-1 font-medium ${openCount ? 'bg-marker-soft text-ink' : 'bg-ok-soft text-ok'}`}>
                {openCount ? <CircleDot size={13} /> : <CheckCircle2 size={13} />}
                {openCount ? t('review.studentsOpen', { n: openCount }) : t('review.allReviewed')}
              </span>
            )}
          </div>
        )}

        {isLoading || !ov || !a ? (
          <div className="flex justify-center py-16 text-ink-muted"><Loader2 className="animate-spin" /></div>
        ) : ov.students.length === 0 ? (
          <div className="mt-6 card px-6 py-12 text-center text-ink-muted">{t('grades.noStudents')}</div>
        ) : (
          <>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <div className="relative w-full max-w-xs">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
                <input className="input pl-9 h-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('grading.search')} aria-label={t('grading.search')} />
              </div>
              <label className="inline-flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" className="w-4 h-4 accent-cobalt" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} />
                {t('review.onlyOpen')}
              </label>
            </div>
            <div className="mt-3 card overflow-x-auto">
              <table className="text-sm border-separate border-spacing-0 w-full">
                <thead>
                  <tr className="text-[12px] text-ink-muted">
                    <th className="sticky left-0 z-10 bg-surface text-left px-4 py-2.5 font-semibold border-b border-line-soft min-w-[11rem]">{t('course.name')}</th>
                    <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-left min-w-[11rem]">{t('review.status')}</th>
                    {a.exam && <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-left">{t('grading.attempt')}</th>}
                    {ov.tasks.map((x, i) => (
                      <th key={x.task_id} className="px-3 py-2.5 font-semibold border-b border-line-soft text-right min-w-[6rem]">
                        <span className="block truncate max-w-[9rem] ml-auto" title={x.title}>{i + 1}. {x.title}</span>
                        <span className="block font-normal">/{fmt(x.points)}{x.variant_group != null ? ` · ${t('variant.short', { n: x.variant_group })}` : ''}
                          {x.kind !== 'code' && <> · {t(`kind.${x.kind}` as any)}</>}</span>
                      </th>
                    ))}
                    <th className="px-4 py-2.5 font-semibold border-b border-line-soft text-right">{t('grades.total')}<span className="block font-normal">/{fmt(ov.max_points)}</span></th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((s) => {
                    const selected = sel?.user === s.user_id
                    const submitted = s.tasks.some((x) => x.submissions > 0)
                    const first = firstToReview(s)
                    return (
                      <tr key={s.user_id} className={selected ? 'bg-marker-soft/60' : 'hover:bg-paper/50'}>
                        <td className={`sticky left-0 z-10 px-4 py-2 border-b border-line-soft ${selected ? 'bg-[#FFF8DB]' : 'bg-surface'}`}>
                          <p className="font-medium truncate max-w-[14rem]">{s.name}</p>
                          <p className="text-[12px] text-ink-muted truncate max-w-[14rem]">{s.group ? `${s.group} · ` : ''}{s.email}</p>
                        </td>
                        <td className="px-3 py-2 border-b border-line-soft">
                          <div className="flex items-center gap-2">
                            {first && (
                              <button onClick={() => pick(s.user_id, first.task_id)} className={`btn-sm ${s.to_review ? 'btn-primary' : 'btn-secondary'}`}>
                                <Eye size={14} /> {t('review.button')}
                              </button>
                            )}
                            {s.to_review > 0 ? <span className="text-[12px] font-semibold text-marker-deep whitespace-nowrap">{t('review.openN', { n: s.to_review })}</span>
                              : submitted ? <span className="text-[12px] font-semibold text-ok whitespace-nowrap inline-flex items-center gap-1"><CheckCircle2 size={12} /> {t('review.done')}</span>
                              : <span className="text-[12px] text-ink-faint whitespace-nowrap">{t('review.nothing')}</span>}
                          </div>
                        </td>
                        {a.exam && <td className="px-3 py-2 border-b border-line-soft"><AttemptCell s={s} /></td>}
                        {ov.tasks.map((x) => {
                          const c = s.tasks.find((y) => y.task_id === x.task_id)
                          const on = selected && sel?.task === x.task_id
                          return (
                            <td key={x.task_id} className="px-1.5 py-1 border-b border-line-soft text-right">
                              {!c ? <span className="px-2 text-ink-faint" title={t('variant.notTheirs')}>·</span> : (
                                <button onClick={() => pick(s.user_id, x.task_id)}
                                  className={`w-full rounded-md px-2 py-1.5 text-right tabular-nums transition-colors ${on ? 'bg-ink text-white' : 'hover:bg-cobalt-soft'}`}
                                  aria-label={t('grading.openCell', { name: s.name, task: x.title })}>
                                  {c.submissions > 0 && !c.reviewed && <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle ${on ? 'bg-white' : 'bg-marker-deep'}`} title={t('review.notYet')} />}
                                  {c.final == null ? <span className={on ? '' : 'text-ink-faint'}>{c.submissions ? (c.kind === 'code' ? '0' : '✓') : '—'}</span>
                                    : <span className={!on && c.final >= c.points ? 'text-ok font-semibold' : ''}>{fmt(c.final)}</span>}
                                  {c.graded && <span className={`ml-1 text-[10px] font-bold ${on ? '' : 'text-cobalt'}`} title={t('grading.adjusted')}>✎</span>}
                                  {c.comment && <MessageSquareText size={11} className="inline ml-0.5 -mt-0.5" />}
                                  {c.more_points && <TrendingUp size={12} className={`inline ml-0.5 -mt-0.5 ${on ? '' : 'text-cobalt'}`} aria-label={t('morePoints.review')} />}
                                </button>
                              )}
                            </td>
                          )
                        })}
                        <td className="px-4 py-2 border-b border-line-soft text-right font-bold tabular-nums">{s.total == null ? '—' : fmt(s.total)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[12px] text-ink-muted">{t('grading.legend2')}</p>
          </>
        )}

        <div ref={reviewRef} className="scroll-mt-4">
          {allDone && (
            <p className="mt-8 card px-5 py-4 text-sm flex items-center gap-2 text-ok font-semibold"><CheckCircle2 size={17} /> {t('review.allReviewed')}</p>
          )}
          {sel && a && !allDone && (
            <ReviewPanel key={`${sel.user}:${sel.task}`} assignment={a} userId={sel.user} taskId={sel.task}
              onSavedNext={async () => next(await qc.fetchQuery({ queryKey: ['overview', assignmentId], queryFn: () => assignmentsApi.overview(assignmentId!) }))} />
          )}
        </div>
      </main>
    </div>
  )
}

function AttemptCell({ s }: { s: Student }) {
  const { t, lang } = useLanguage()
  if (!s.attempt) return <span className="text-[12px] text-ink-faint">{t('grading.notStarted')}</span>
  const blur = s.signals.blur ?? 0, paste = s.signals.paste ?? 0
  return (
    <div className="text-[12px] leading-tight whitespace-nowrap">
      <p className="text-ink-soft">{formatDateTime(s.attempt.started_at, lang)}</p>
      <p className="mt-0.5 flex items-center gap-2 text-ink-muted">
        {s.attempt.finished_at && <span className="inline-flex items-center gap-0.5" title={t('grading.handedIn')}><Flag size={11} /></span>}
        <span className={`inline-flex items-center gap-0.5 ${blur >= 3 ? 'text-bad font-semibold' : ''}`} title={t('signals.blur')}><LogOut size={11} /> {blur}</span>
        <span className={`inline-flex items-center gap-0.5 ${paste ? 'text-bad font-semibold' : ''}`} title={t('signals.paste')}><Clipboard size={11} /> {paste}</span>
        <span className="font-mono text-[11px]">{s.attempt.ip}</span>
      </p>
    </div>
  )
}

function ReviewPanel({ assignment, userId, taskId, onSavedNext }: { assignment: Assignment; userId: string; taskId: string; onSavedNext: () => void }) {
  const { t, tError, lang } = useLanguage()
  const qc = useQueryClient()
  const key = ['review', assignment.id, userId, taskId]
  const { data: r, isLoading } = useQuery<Review>({ queryKey: key, queryFn: () => assignmentsApi.review(assignment.id, userId, taskId) })
  const [subId, setSubId] = useState<string | null>(null)
  const [adjust, setAdjust] = useState('0')
  const [override, setOverride] = useState('')
  const [comment, setComment] = useState('')
  const [scores, setScores] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!r) return
    setAdjust(String(r.grade?.adjust ?? 0)); setOverride(r.grade?.override != null ? String(r.grade.override) : ''); setComment(r.grade?.comment ?? '')
    setScores(Object.fromEntries((r.task.rubric ?? []).map((c) => [c.id, r.grade?.rubric_scores?.[c.id] != null ? String(r.grade.rubric_scores[c.id]) : ''])))
  }, [r?.grade?.updated_at, r != null]) // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading || !r) return <div className="mt-8 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>

  const kind = r.task.kind
  const canGrade = ['teacher', 'assistant', 'lab'].includes(assignment.my_role ?? '')   // professor, assistant and лаборант set points
  const canComment = canGrade   // whoever enters the points also explains them on the code
  const rubric = r.task.rubric ?? []
  const best = kind === 'code'
    ? r.submissions.reduce<Review['submissions'][number] | null>((b, s) => (!b || s.score > b.score ? s : b), null)
    : r.submissions[0] ?? null  // files: the latest upload is graded
  const shown = r.submissions.find((s) => s.id === subId) ?? best
  const adj = parseFloat(adjust) || 0
  const ov = override.trim() === '' ? null : parseFloat(override)
  const rubricTotal = rubric.reduce((n, c) => n + c.points, 0)
  const rubricGot = rubric.reduce((n, c) => n + (parseFloat(scores[c.id]) || 0), 0)
  const useRubric = rubric.length > 0
  const preview = useRubric ? (rubricTotal ? (r.task.points * rubricGot) / rubricTotal : 0)
    : ov != null && !isNaN(ov) ? ov : r.best == null ? null : Math.min(Math.max(r.best + adj, 0), r.task.points)
  const refresh = () => { qc.invalidateQueries({ queryKey: key }); qc.invalidateQueries({ queryKey: ['overview', assignment.id] }) }

  const save = async (andNext: boolean) => {
    setSaving(true); setMsg('')
    try {
      await assignmentsApi.setGrade(assignment.id, {
        user_id: userId, task_id: taskId, comment,
        adjust: useRubric || kind !== 'code' ? 0 : adj,
        override: useRubric ? null : ov,
        rubric_scores: useRubric ? Object.fromEntries(rubric.map((c) => [c.id, Math.min(c.points, Math.max(0, parseFloat(scores[c.id]) || 0))])) : null,
      })
      qc.invalidateQueries({ queryKey: ['gradebook'] })
      if (andNext) { qc.invalidateQueries({ queryKey: key }); onSavedNext() }
      else { setMsg(t('course.saved')); refresh() }
    } catch (err: any) {
      setMsg(tError(err.response?.data?.detail, 'course.actionFailed'))
    } finally { setSaving(false) }
  }

  const kindIcon = kind === 'document' ? <FileText size={13} /> : kind === 'project' ? <FolderArchive size={13} /> : kind === 'offline' ? <ClipboardCheck size={13} /> : null
  return (
    <section className="mt-8 card p-5 sm:p-6">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex-1 min-w-[14rem]">
          <p className="text-[12px] text-ink-muted">{r.student.email}</p>
          <h2 className="text-xl font-bold">{r.student.name}</h2>
          <p className="mt-0.5 text-sm text-ink-soft flex items-center gap-2">
            {kind === 'code' ? <LangChip lang={r.task.language} /> : <span className="inline-flex items-center gap-1 text-[12px] font-semibold">{kindIcon} {t(`kind.${kind}` as any)}</span>}
            {r.task.title}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-ink-muted">{t('grading.final')}</p>
          <p className="text-3xl font-extrabold tabular-nums">{r.final == null ? '—' : fmt(r.final)}<span className="text-base text-ink-muted font-semibold"> / {fmt(r.task.points)}</span></p>
          <p className={`text-[12px] font-semibold ${r.grade ? 'text-ok' : 'text-marker-deep'}`}>{r.grade ? t('review.done') : t('review.notYet')}</p>
        </div>
      </div>

      <div className="mt-5 grid lg:grid-cols-[minmax(0,1fr)_18rem] gap-5">
        <div className="min-w-0">
          {kind === 'offline' ? (
            <p className="text-sm text-ink-muted card px-4 py-8 text-center">{t('review.offline')}</p>
          ) : r.submissions.length === 0 ? (
            <p className="text-sm text-ink-muted card px-4 py-8 text-center">{t('grading.noSubmissions')}</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-1.5" role="tablist" aria-label={t('grading.submissions')}>
                {r.submissions.map((s, i) => (
                  <button key={s.id} role="tab" aria-selected={shown?.id === s.id} onClick={() => setSubId(s.id)}
                    className={`text-[12px] rounded-full px-2.5 py-1 border tabular-nums inline-flex items-center gap-1 ${
                      shown?.id === s.id ? 'bg-ink text-white border-ink' : 'bg-surface border-line hover:border-ink-faint'}`}>
                    {s.id === best?.id && <Star size={11} className={shown?.id === s.id ? '' : 'text-marker-deep'} fill="currentColor" />}
                    #{r.submissions.length - i} · {kind === 'code' ? `${s.passed}/${s.total} · ${fmt(s.score)}` : formatSize(s.file_size)}{s.late ? ' L' : ''}
                    {s.comments.length > 0 && <MessageSquareText size={11} />}
                  </button>
                ))}
              </div>
              {shown && (
                <div className="mt-2">
                  <p className="mb-1.5 text-[12px] text-ink-muted">
                    {formatDateTime(shown.submitted_at, lang)}{kind !== 'document' && ` · ${t('grading.clickLine')}`}
                  </p>
                  {kind === 'code' && diagramKindOf(shown.code) ? (
                    <div className="space-y-3">
                      <div className="card overflow-hidden h-[30rem]"><DiagramEditor code={shown.code} kind={diagramKindOf(shown.code)!} readOnly /></div>
                      {shown.file_name && (
                        <div>
                          <p className="mb-1.5 text-[12px] text-ink-muted">{t('dg.originalPicture')}</p>
                          <FilePreview submissionId={shown.id} fileType={shown.file_type} fileName={shown.file_name} />
                        </div>
                      )}
                    </div>
                  ) : kind === 'code' && r.task.language === 'web' ? (
                    <WebSubmissionView code={shown.code}>
                      <CodeView code={shown.code} comments={shown.comments}
                        onAdd={canComment ? async (line, body) => { await assignmentsApi.addComment(shown.id, line, body); refresh() } : undefined}
                        onDelete={canComment ? async (id) => { await assignmentsApi.deleteComment(id); refresh() } : undefined} />
                    </WebSubmissionView>
                  ) : kind === 'code' ? (
                    <CodeView code={shown.code} comments={shown.comments}
                      onAdd={canComment ? async (line, body) => { await assignmentsApi.addComment(shown.id, line, body); refresh() } : undefined}
                      onDelete={canComment ? async (id) => { await assignmentsApi.deleteComment(id); refresh() } : undefined} />
                  ) : kind === 'project' ? (
                    <ProjectBrowser submissionId={shown.id} comments={shown.comments}
                      onAdd={canComment ? async (path, line, body) => { await assignmentsApi.addComment(shown.id, line, body, path); refresh() } : undefined}
                      onDelete={canComment ? async (id) => { await assignmentsApi.deleteComment(id); refresh() } : undefined} />
                  ) : (
                    <FilePreview submissionId={shown.id} fileType={shown.file_type} fileName={shown.file_name} />
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <aside className="space-y-4">
          {r.task.reference_file && (
            <button type="button" onClick={() => adminApi.downloadReference(r.task.task_id, r.task.reference_file!.name)}
              className="w-full card px-3.5 py-2.5 flex items-center gap-2 text-left text-sm hover:border-cobalt">
              <Download size={15} className="text-cobalt shrink-0" />
              <span className="min-w-0"><span className="block text-[12px] text-ink-muted">{t('reference.title')}</span>
                <span className="block truncate font-medium">{r.task.reference_file.name}</span></span>
            </button>
          )}
          {!canGrade ? (
            <div className="rounded-lg border border-line p-4 space-y-2">
              <p className="text-sm"><span className="text-ink-muted">{t('grading.auto')}</span> <span className="font-bold tabular-nums">{r.best == null ? '—' : fmt(r.best)}</span> / {fmt(r.task.points)}</p>
              {r.grade?.comment && <p className="text-[13px] whitespace-pre-line"><span className="text-ink-muted">{t('grading.comment')}:</span> {r.grade.comment}</p>}
            </div>
          ) : <div className="rounded-lg border border-line p-4 space-y-3">
            {(shown?.code ?? '').trim() !== '' && (
              <GradingTutor assignmentId={assignment.id} userId={userId} taskId={taskId} rubric={rubric}
                onApply={(sug) => {
                  if (useRubric && sug.rubric_scores) setScores(Object.fromEntries(rubric.map((c) => [c.id, sug.rubric_scores![c.id] != null ? String(sug.rubric_scores![c.id]) : ''])))
                  else setOverride(String(sug.points))
                  if (sug.comment) setComment(sug.comment)
                }}
                onComment={canComment && shown ? async (line, body) => { await assignmentsApi.addComment(shown.id, line, body); refresh() } : undefined} />
            )}
            {useRubric ? (
              <div>
                <p className="field-label">{t('rubric.title')}</p>
                <ul className="space-y-2">
                  {rubric.map((c) => (
                    <li key={c.id} className="flex items-center gap-2">
                      <label htmlFor={`rb-${c.id}`} className="flex-1 min-w-0 text-[13px]">{c.title}</label>
                      <input id={`rb-${c.id}`} type="number" min={0} max={c.points} step={0.5} className="input h-8 w-16 text-right"
                        value={scores[c.id] ?? ''} onChange={(e) => setScores((p) => ({ ...p, [c.id]: e.target.value }))} />
                      <span className="text-[12px] text-ink-muted tabular-nums w-10">/ {fmt(c.points)}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[12px] text-ink-muted tabular-nums">{t('rubric.sum', { got: fmt(rubricGot), of: fmt(rubricTotal) })}</p>
              </div>
            ) : (
              <>
                {kind === 'code' && (
                  <>
                    <p className="text-sm"><span className="text-ink-muted">{t('grading.auto')}</span> <span className="font-bold tabular-nums">{r.best == null ? '—' : fmt(r.best)}</span></p>
                    <div>
                      <label htmlFor="g-adj" className="field-label">{t('grading.adjust')}</label>
                      <input id="g-adj" type="number" step={0.5} className="input h-9" value={adjust} onChange={(e) => setAdjust(e.target.value)} disabled={ov != null} />
                      <p className="field-hint">{t('grading.adjustHint')}</p>
                    </div>
                  </>
                )}
                <div>
                  <label htmlFor="g-ov" className="field-label">{kind === 'code' ? t('grading.override') : t('grading.points')}</label>
                  <input id="g-ov" type="number" step={0.5} min={0} max={r.task.points} className="input h-9" value={override} onChange={(e) => setOverride(e.target.value)}
                    placeholder={kind === 'code' ? t('grading.overridePlaceholder') : `0 – ${fmt(r.task.points)}`} />
                </div>
              </>
            )}
            <div>
              <label htmlFor="g-c" className="field-label">{t('grading.comment')}</label>
              <textarea id="g-c" rows={4} className="input h-auto py-2 text-[13px]" value={comment} onChange={(e) => setComment(e.target.value)}
                placeholder={t('grading.commentPlaceholder')} />
            </div>
            <p className="text-sm">{t('grading.willBe')} <span className="font-bold tabular-nums">{preview == null ? '—' : fmt(preview)} / {fmt(r.task.points)}</span></p>
            <button onClick={() => save(true)} disabled={saving} className="btn-primary w-full">
              {saving ? <Loader2 size={15} className="animate-spin" /> : <SkipForward size={15} />} {t('review.saveNext')}
            </button>
            <button onClick={() => save(false)} disabled={saving} className="btn-secondary w-full">
              <Save size={15} /> {t('grading.save')}
            </button>
            {msg && <p className="text-[13px] text-ink-muted" role="status">{msg}</p>}
            {!assignment.grades_published && <p className="text-[12px] text-ink-muted">{t('grading.notVisibleYet')}</p>}
          </div>}

          {assignment.exam && (
            <div className="rounded-lg border border-line p-4">
              <h3 className="text-sm font-bold">{t('signals.title')}</h3>
              <p className="mt-0.5 text-[12px] text-ink-muted">{t('signals.hint')}</p>
              {r.events.length === 0 ? <p className="mt-2 text-[13px] text-ink-muted">—</p> : (
                <ol className="mt-2 space-y-1 max-h-64 overflow-y-auto text-[12px]">
                  {r.events.map((e, i) => (
                    <li key={i} className={`flex gap-2 ${e.kind === 'paste' || e.kind === 'blur' ? 'text-bad' : 'text-ink-soft'}`}>
                      <span className="tabular-nums text-ink-muted shrink-0">{new Date(e.created_at).toLocaleTimeString('en-GB')}</span>
                      <span>{t(`signals.${e.kind}` as any)}{e.detail ? ` · ${e.detail}` : ''}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}


/** The grading tutor: the AI reads the solution, the tests and the rubric and suggests points, what is good, the
 *  issues by line and a comment for the student. The grader decides — nothing is saved until they save. */
function GradingTutor({ assignmentId, userId, taskId, rubric, onApply, onComment }: {
  assignmentId: string; userId: string; taskId: string; rubric: { id: string; title: string; points: number }[]
  onApply: (s: GradingSuggestion) => void; onComment?: (line: number, body: string) => Promise<void>
}) {
  const { t, tError } = useLanguage()
  const [sug, setSug] = useState<GradingSuggestion | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [added, setAdded] = useState<number[]>([])
  useEffect(() => { setSug(null); setErr(''); setAdded([]) }, [userId, taskId])

  const ask = async () => {
    setBusy(true); setErr('')
    try { setSug(await assignmentsApi.gradingAssist(assignmentId, userId, taskId)); setAdded([]) }
    catch (e: any) { setErr(tError(e.response?.data?.detail, 'gtutor.error')) }
    finally { setBusy(false) }
  }

  if (!sug) return (
    <div>
      <button type="button" onClick={ask} disabled={busy} className="btn-secondary w-full">
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {busy ? t('gtutor.reading') : t('gtutor.ask')}
      </button>
      {err && <p className="mt-1.5 text-[12.5px] text-bad" role="alert">{err}</p>}
    </div>
  )
  return (
    <div className="rounded-lg bg-ink text-white p-3.5 space-y-2.5" aria-live="polite">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[12px] text-white/60 flex items-center gap-1.5"><Sparkles size={13} className="text-marker" /> {t('gtutor.title')}</p>
        <p className="font-extrabold tabular-nums">{fmt(sug.points)} <span className="text-white/50 font-semibold text-[12px]">/ {fmt(sug.max_points)}</span></p>
      </div>
      {sug.rubric_scores && rubric.length > 0 && (
        <ul className="text-[12px] space-y-0.5">
          {rubric.map((c) => <li key={c.id} className="flex justify-between gap-2"><span className="text-white/70 truncate">{c.title}</span>
            <span className="tabular-nums">{sug.rubric_scores![c.id] != null ? fmt(sug.rubric_scores![c.id]) : '—'} / {fmt(c.points)}</span></li>)}
        </ul>
      )}
      {sug.summary && <p className="text-[13px]">{sug.summary}</p>}
      {sug.strengths.length > 0 && (
        <ul className="text-[12.5px] text-white/80 space-y-0.5">{sug.strengths.map((x, i) => <li key={i}>+ {x}</li>)}</ul>
      )}
      {sug.issues.length > 0 && (
        <ul className="text-[12.5px] space-y-1.5">
          {sug.issues.map((x, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="font-mono text-[11px] text-marker shrink-0 mt-px w-9">{x.line ? `${t('gtutor.line')} ${x.line}` : '—'}</span>
              <span className="flex-1">{x.note}</span>
              {x.line && onComment && (
                <button type="button" disabled={added.includes(i)} className="shrink-0 text-[11.5px] text-white/70 hover:text-white disabled:text-white/40 inline-flex items-center gap-0.5"
                  onClick={async () => { await onComment(x.line!, x.note); setAdded((p) => [...p, i]) }}>
                  {added.includes(i) ? <CheckCircle2 size={12} /> : <Plus size={12} />} {added.includes(i) ? t('gtutor.added') : t('gtutor.toComment')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {sug.comment && <p className="text-[12.5px] text-white/70 border-l-2 border-marker pl-2">{sug.comment}</p>}
      <div className="flex gap-2 pt-0.5">
        <button type="button" onClick={() => onApply(sug)} className="flex-1 rounded-md bg-marker text-ink font-bold text-[13px] py-1.5 hover:brightness-95">{t('gtutor.apply')}</button>
        <button type="button" onClick={ask} disabled={busy} className="rounded-md border border-white/25 text-[13px] px-3 hover:bg-white/10">
          {busy ? <Loader2 size={14} className="animate-spin" /> : t('gtutor.again')}
        </button>
      </div>
      <p className="text-[11px] text-white/45">{t('gtutor.note')}</p>
    </div>
  )
}
