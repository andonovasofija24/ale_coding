import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowLeft, ArrowUp, Bot, BotOff, Lightbulb, Loader2, Plus, Save, Search, Sparkles, Timer, Trash2, X } from 'lucide-react'
import { assignmentsApi, coursesApi, subjectsApi } from '../services/api'
import { langClass, langInfo } from '../lib/languages'
import { useLanguage } from '../i18n/LanguageContext'
import { AIMode, Assignment, AssignmentKind, CourseDetail, ResultsVisibility, SubjectDetail, TaskListItem } from '../types'
import { fromLocalInput, toLocalInput } from '../lib/time'
import AppHeader from '../components/AppHeader'
import TaskChip from '../components/TaskChip'
import { fmt } from '../components/course/bits'

interface Picked { task_id: string; title: string; language: string; points: number; variant_group: number | null; kind?: string }

/** Staff: create / edit an assignment — when it opens and is due, late policy, group, and which tasks (with points). */
export default function AssignmentFormPage() {
  const { courseId: courseParam, assignmentId } = useParams<{ courseId?: string; assignmentId?: string }>()
  const isEdit = !!assignmentId
  const { t, tError } = useLanguage()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: existing } = useQuery<Assignment>({
    queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!), enabled: isEdit,
  })
  const courseId = courseParam ?? existing?.course_id
  const { data: course } = useQuery<CourseDetail>({
    queryKey: ['course', courseId], queryFn: () => coursesApi.get(courseId!), enabled: !!courseId,
  })
  // the course's task bank (a лаборант has no access to the admin bank)
  const { data: bank = [] } = useQuery<TaskListItem[]>({ queryKey: ['task-bank', courseId], queryFn: () => assignmentsApi.taskBank(courseId!), enabled: !!courseId })
  const isLab = course?.my_role === 'lab'   // a лаборант: only labs / practice, counted as labs

  const [title, setTitle] = useState('')
  const [kind, setKind] = useState<AssignmentKind>('lab')
  const [description, setDescription] = useState('')
  const [groupId, setGroupId] = useState('')
  const [opensAt, setOpensAt] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [allowLate, setAllowLate] = useState(false)
  const [penalty, setPenalty] = useState(20)
  const [published, setPublished] = useState(false)
  const [tasks, setTasks] = useState<Picked[]>([])
  const [aiMode, setAiMode] = useState<AIMode>('full')
  const [hintLimit, setHintLimit] = useState(3)
  const [duration, setDuration] = useState('')
  const [allowedIps, setAllowedIps] = useState('')
  const [visibility, setVisibility] = useState<ResultsVisibility>('full')
  const [afterPublish, setAfterPublish] = useState(false)
  const [reviewOn, setReviewOn] = useState(true)
  const [reviewThreshold, setReviewThreshold] = useState(85)
  const [improveLimit, setImproveLimit] = useState(2)
  const [category, setCategory] = useState<string>('')   // '' = by kind
  const [practiceFor, setPracticeFor] = useState<string>('')   // a practice assignment for a colloquium / the exam
  const [gen, setGen] = useState(false)
  const [editorChecks, setEditorChecks] = useState(true)
  const exam = kind === 'exam'
  const [search, setSearch] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!existing) return
    setTitle(existing.title); setKind(existing.kind); setDescription(existing.description)
    setGroupId(existing.group_id ?? ''); setOpensAt(toLocalInput(existing.opens_at)); setDueAt(toLocalInput(existing.due_at))
    setAllowLate(existing.allow_late); setPenalty(existing.late_penalty); setPublished(existing.published)
    setTasks(existing.tasks.map((x) => ({ task_id: x.task_id, title: x.title, language: x.language, points: x.points, variant_group: x.variant_group ?? null, kind: x.kind })))
    setAiMode(existing.ai_mode); setHintLimit(existing.hint_limit); setDuration(existing.duration_minutes ? String(existing.duration_minutes) : '')
    setAllowedIps(existing.allowed_ips ?? ''); setVisibility(existing.results_visibility); setAfterPublish(existing.scores_after_publish)
    setReviewOn(existing.review_threshold > 0); setReviewThreshold(existing.review_threshold || 85); setImproveLimit(existing.improve_limit)
    setCategory(existing.category ?? '')
    setPracticeFor(existing.practice_for ?? '')
    setEditorChecks(existing.editor_checks ?? true)
  }, [existing])

  const results = useMemo(() => {
    const q = search.trim().toLowerCase()
    const chosen = new Set(tasks.map((x) => x.task_id))
    return bank.filter((b) => !chosen.has(b.id) && (!q || b.title.toLowerCase().includes(q) || b.language.includes(q))).slice(0, 8)
  }, [bank, search, tasks])

  const move = (i: number, d: number) => setTasks((prev) => {
    const next = [...prev]; const j = i + d
    if (j < 0 || j >= next.length) return prev
    ;[next[i], next[j]] = [next[j], next[i]]
    return next
  })

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (opensAt && dueAt && new Date(dueAt) <= new Date(opensAt)) { setError(t('assign.dueBeforeOpen')); return }
    setSaving(true)
    const body = {
      title, kind, description, group_id: groupId || null,
      opens_at: fromLocalInput(opensAt), due_at: fromLocalInput(dueAt),
      allow_late: allowLate && !exam, late_penalty: allowLate && !exam ? penalty : 0, published,
      tasks: tasks.map((x) => ({ task_id: x.task_id, points: x.points, variant_group: x.variant_group })),
      ai_mode: aiMode, hint_limit: hintLimit, exam, duration_minutes: exam && duration ? parseInt(duration) : null,
      allowed_ips: allowedIps, results_visibility: visibility, scores_after_publish: afterPublish,
      review_threshold: reviewOn ? reviewThreshold : 0, improve_limit: improveLimit,
      category: kind === 'practice' && practiceFor ? 'none' : category || null,
      practice_for: kind === 'practice' ? practiceFor || null : null,
      editor_checks: editorChecks,
    }
    try {
      const saved: Assignment = isEdit ? await assignmentsApi.update(assignmentId!, body) : await coursesApi.createAssignment(courseId!, body)
      qc.invalidateQueries({ queryKey: ['course', courseId] })
      qc.invalidateQueries({ queryKey: ['assignment', saved.id] })
      qc.invalidateQueries({ queryKey: ['gradebook', courseId] })
      navigate(`/assignments/${saved.id}`)
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'assign.saveFailed'))
    } finally { setSaving(false) }
  }

  const remove = async () => {
    if (!confirm(t('assign.deleteConfirm', { title }))) return
    await assignmentsApi.remove(assignmentId!)
    qc.invalidateQueries({ queryKey: ['course', courseId] })
    navigate(`/courses/${courseId}`)
  }

  if (isEdit && !existing) return <div className="flex items-center justify-center h-screen text-ink-muted"><Loader2 className="animate-spin" /></div>

  // Each variant group counts once (with its most valuable task) — every student gets one task from it.
  const groupMax = new Map<number, number>()
  tasks.forEach((x) => { if (x.variant_group != null) groupMax.set(x.variant_group, Math.max(groupMax.get(x.variant_group) ?? 0, Number(x.points) || 0)) })
  const total = tasks.filter((x) => x.variant_group == null).reduce((n, x) => n + (Number(x.points) || 0), 0) + [...groupMax.values()].reduce((n, v) => n + v, 0)

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <Link to={isEdit ? `/assignments/${assignmentId}` : `/courses/${courseId}`} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {course ? `${course.code} · ${course.name}` : t('courses.all')}
        </Link>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight">{isEdit ? t('assign.edit') : t('assign.new')}</h1>

        <form onSubmit={save} className="mt-6 space-y-5">
          <section className="card p-5 sm:p-6 space-y-4">
            <div className="grid sm:grid-cols-[minmax(0,1fr)_10rem] gap-3">
              <div>
                <label htmlFor="a-title" className="field-label">{t('assign.title')}</label>
                <input id="a-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={300}
                  placeholder={t('assign.titlePlaceholder')} />
              </div>
              <div>
                <label htmlFor="a-kind" className="field-label">{t('assign.kind')}</label>
                <select id="a-kind" className="input" value={kind} onChange={(e) => setKind(e.target.value as AssignmentKind)}>
                  {((isLab ? ['lab', 'practice'] : ['lab', 'homework', 'practice', 'exam']) as AssignmentKind[]).map((k) => <option key={k} value={k}>{t(`akind.${k}` as any)}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label htmlFor="a-desc" className="field-label">{t('assign.description')}</label>
              <textarea id="a-desc" rows={3} className="input h-auto py-2" value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder={t('assign.descriptionPlaceholder')} />
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="a-group" className="field-label">{t('assign.for')}</label>
                <select id="a-group" className="input" value={groupId} onChange={(e) => setGroupId(e.target.value)}>
                  <option value="">{t('assign.wholeCourse')}</option>
                  {course?.groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="a-cat" className="field-label">{t('assign.category')}</label>
                <select id="a-cat" className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="">{t('assign.categoryAuto', { cat: t(`gcat.${({ lab: 'labs', homework: 'homework', exam: 'exam' } as Record<string, string>)[kind] ?? 'none'}` as any) })}</option>
                  {(isLab ? ['labs', 'none'] : ['labs', 'homework', 'k1', 'k2', 'exam', 'none']).map((c) => <option key={c} value={c}>{t(`gcat.${c}` as any)}</option>)}
                </select>
              </div>
            </div>
            <p className="-mt-2 text-[12px] text-ink-muted">{t('assign.categoryHint')}</p>
            {kind === 'practice' && (
              <div>
                <label htmlFor="a-prep" className="field-label">{t('prep.label')}</label>
                <select id="a-prep" className="input" value={practiceFor} onChange={(e) => setPracticeFor(e.target.value)}>
                  <option value="">{t('prep.none')}</option>
                  {['k1', 'k2', 'exam'].map((c) => <option key={c} value={c}>{t(`gcat.${c}` as any)}</option>)}
                </select>
                <p className="field-hint">{t('prep.hint')}</p>
              </div>
            )}
          </section>

          <section className="card p-5 sm:p-6 space-y-4">
            <h2 className="font-bold">{t('assign.timing')}</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="a-open" className="field-label">{t('assign.opensAt')}</label>
                <input id="a-open" type="datetime-local" className="input" value={opensAt} onChange={(e) => setOpensAt(e.target.value)} />
                <p className="field-hint">{t('assign.opensAtHint')}</p>
              </div>
              <div>
                <label htmlFor="a-due" className="field-label">{t('assign.dueAt')}</label>
                <input id="a-due" type="datetime-local" className="input" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
                <p className="field-hint">{t('assign.dueAtHint')}</p>
              </div>
            </div>
            {exam ? (
              <div className="grid sm:grid-cols-2 gap-3 border-t border-line-soft pt-4">
                <div>
                  <label htmlFor="a-dur" className="field-label flex items-center gap-1.5"><Timer size={14} /> {t('exam.duration')}</label>
                  <input id="a-dur" type="number" min={1} max={1440} className="input" value={duration} onChange={(e) => setDuration(e.target.value)}
                    placeholder={t('exam.durationPlaceholder')} />
                  <p className="field-hint">{t('exam.durationHint')}</p>
                </div>
                <div>
                  <label htmlFor="a-ips" className="field-label">{t('exam.allowedIps')}</label>
                  <input id="a-ips" className="input font-mono text-[13px]" value={allowedIps} onChange={(e) => setAllowedIps(e.target.value)}
                    placeholder="194.149.135.0/24, 194.149.136.0/24" />
                  <p className="field-hint">{t('exam.allowedIpsHint')}</p>
                </div>
              </div>
            ) : (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <label className="inline-flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" className="w-4 h-4 accent-cobalt" checked={allowLate} onChange={(e) => setAllowLate(e.target.checked)} disabled={!dueAt} />
                {t('assign.allowLate')}
              </label>
              {allowLate && (
                <label className="inline-flex items-center gap-2 text-sm">
                  {t('assign.penalty')}
                  <input type="number" min={0} max={100} className="input h-8 w-20" value={penalty}
                    onChange={(e) => setPenalty(Math.max(0, Math.min(100, parseInt(e.target.value) || 0)))} /> %
                </label>
              )}
            </div>
            )}
          </section>

          <section className="card p-5 sm:p-6 space-y-4">
            <div>
              <h2 className="font-bold">{t('ai.rulesTitle')}</h2>
              <p className="mt-0.5 text-[13px] text-ink-muted">{t('ai.rulesHint')}</p>
            </div>
            <div className="grid sm:grid-cols-3 gap-2" role="radiogroup" aria-label={t('ai.rulesTitle')}>
              {([['full', <Bot size={16} />], ['hints', <Lightbulb size={16} />], ['off', <BotOff size={16} />]] as [AIMode, JSX.Element][]).map(([m, icon]) => (
                <label key={m} className={`cursor-pointer rounded-lg border px-3 py-2.5 ${aiMode === m ? 'border-ink bg-paper ring-1 ring-ink' : 'border-line hover:border-ink-faint'}`}>
                  <input type="radio" name="ai-mode" className="sr-only" checked={aiMode === m} onChange={() => setAiMode(m)} />
                  <span className="flex items-center gap-1.5 text-sm font-semibold">{icon} {t(`ai.mode.${m}` as any)}</span>
                  <span className="block mt-0.5 text-[12px] text-ink-muted leading-snug">{t(`ai.mode.${m}.hint` as any)}</span>
                </label>
              ))}
            </div>
            {aiMode === 'hints' && (
              <div className="flex flex-wrap gap-x-6 gap-y-2">
                <label className="inline-flex items-center gap-2 text-sm">
                  {t('ai.hintLimit')}
                  <input type="number" min={0} max={50} className="input h-8 w-20" value={hintLimit}
                    onChange={(e) => setHintLimit(Math.max(0, Math.min(50, parseInt(e.target.value) || 0)))} />
                </label>
                <label className="inline-flex items-center gap-2 text-sm">
                  {t('ai.improveLimit')}
                  <input type="number" min={0} max={20} className="input h-8 w-20" value={improveLimit}
                    onChange={(e) => setImproveLimit(Math.max(0, Math.min(20, parseInt(e.target.value) || 0)))} />
                </label>
              </div>
            )}
            <label className="flex items-start gap-3 cursor-pointer pt-1">
              <input type="checkbox" className="w-4 h-4 mt-0.5 accent-cobalt" checked={editorChecks} onChange={(e) => setEditorChecks(e.target.checked)} />
              <span>
                <span className="font-semibold text-sm">{t('diag.setting')}</span>
                <span className="block text-[13px] text-ink-muted">{t('diag.settingHint')}</span>
              </span>
            </label>
          </section>

          <section className="card p-5 sm:p-6 space-y-4">
            <h2 className="font-bold">{t('results.sectionTitle')}</h2>
            <div>
              <label htmlFor="a-vis" className="field-label">{t('results.visibility')}</label>
              <select id="a-vis" className="input" value={visibility} onChange={(e) => setVisibility(e.target.value as ResultsVisibility)}>
                {(['full', 'summary', 'none'] as ResultsVisibility[]).map((v) => <option key={v} value={v}>{t(`results.opt.${v}` as any)}</option>)}
              </select>
            </div>
            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 mt-0.5 accent-cobalt" checked={afterPublish} onChange={(e) => setAfterPublish(e.target.checked)} />
              <span>
                <span className="font-semibold text-sm">{t('results.afterPublish')}</span>
                <span className="block text-[13px] text-ink-muted">{t('results.afterPublishHint')}</span>
              </span>
            </label>
            <div className="flex items-start gap-3">
              <input id="a-review" type="checkbox" className="w-4 h-4 mt-0.5 accent-cobalt" checked={reviewOn} onChange={(e) => setReviewOn(e.target.checked)} />
              <div>
                <label htmlFor="a-review" className="font-semibold text-sm cursor-pointer">{t('morePoints.setting')}</label>
                <span className="block text-[13px] text-ink-muted">{t('morePoints.settingHint')}</span>
                {reviewOn && (
                  <label className="mt-2 inline-flex items-center gap-2 text-sm">
                    {t('morePoints.threshold')}
                    <input type="number" min={1} max={99} className="input h-8 w-20" value={reviewThreshold}
                      onChange={(e) => setReviewThreshold(Math.max(1, Math.min(99, parseInt(e.target.value) || 85)))} /> %
                  </label>
                )}
              </div>
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-bold">{t('assign.tasks')}</h2>
              <span className="text-sm text-ink-muted tabular-nums">{t('assign.totalPoints', { n: fmt(total) })}</span>
            </div>
            {tasks.length === 0 ? (
              <p className="mt-3 text-sm text-ink-muted">{t('assign.noTasksYet')}</p>
            ) : (
              <ol className="mt-3 divide-y divide-line-soft border border-line-soft rounded-lg">
                {tasks.map((x, i) => (
                  <li key={x.task_id} className="flex items-center gap-3 px-3 py-2">
                    <span className="text-sm font-bold text-ink-muted w-5">{i + 1}</span>
                    <TaskChip kind={x.kind} lang={x.language} />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{x.title}</span>
                    <select className="input h-8 w-auto text-[12px] px-2" value={x.variant_group ?? ''} aria-label={t('variant.label')} title={t('variant.hint')}
                      onChange={(e) => setTasks((p) => p.map((y, j) => (j === i ? { ...y, variant_group: e.target.value ? parseInt(e.target.value) : null } : y)))}>
                      <option value="">{t('variant.none')}</option>
                      {[1, 2, 3, 4, 5].map((g) => <option key={g} value={g}>{t('variant.short', { n: g })}</option>)}
                    </select>
                    <label className="inline-flex items-center gap-1 text-[13px] text-ink-muted">
                      <input type="number" min={0} max={1000} step={0.5} className="input h-8 w-20 text-right" value={x.points}
                        aria-label={t('assign.points')}
                        onChange={(e) => setTasks((p) => p.map((y, j) => (j === i ? { ...y, points: parseFloat(e.target.value) || 0 } : y)))} />
                      {t('assign.pointsShort')}
                    </label>
                    <button type="button" onClick={() => move(i, -1)} className="btn-ghost btn-sm px-1.5" aria-label={t('assign.up')}><ArrowUp size={14} /></button>
                    <button type="button" onClick={() => move(i, 1)} className="btn-ghost btn-sm px-1.5" aria-label={t('assign.down')}><ArrowDown size={14} /></button>
                    <button type="button" onClick={() => setTasks((p) => p.filter((_, j) => j !== i))} className="btn-ghost btn-sm px-1.5 text-ink-muted hover:text-bad"
                      aria-label={t('assign.removeTask')}><X size={15} /></button>
                  </li>
                ))}
              </ol>
            )}
            {tasks.length > 1 && <p className="mt-2 text-[12px] text-ink-muted">{t('variant.explain')}</p>}
            {course?.subject_id && (
              <button type="button" onClick={() => setGen(true)}
                className="mt-4 w-full rounded-xl border-2 border-ink bg-ink text-white px-4 py-3 text-left flex items-center gap-3 hover:bg-black">
                <Sparkles size={18} className="text-marker shrink-0" />
                <span className="min-w-0 flex-1"><span className="block font-bold text-[14px]">{t('gen.open')}</span>
                  <span className="block text-[12.5px] text-white/65">{t('gen.openHint')}</span></span>
              </button>
            )}
            <div className="mt-4">
              <label htmlFor="a-search" className="field-label">{t('assign.addFromBank')}</label>
              <div className="relative">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
                <input id="a-search" className="input pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('assign.searchBank')} />
              </div>
              <ul className="mt-2 space-y-1">
                {results.map((b) => (
                  <li key={b.id}>
                    <button type="button" onClick={() => setTasks((p) => [...p, { task_id: b.id, title: b.title, language: b.language, points: 10, variant_group: null, kind: b.kind }])}
                      className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left hover:bg-paper border border-transparent hover:border-line-soft">
                      <Plus size={14} className="text-cobalt" />
                      <TaskChip kind={b.kind} lang={b.language} />
                      <span className="flex-1 truncate text-sm">{b.title}</span>
                      {b.is_public === false && <span className="text-[11px] text-ink-muted">{t('form.courseOnly')}</span>}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[12px] text-ink-muted">
                {t('assign.bankHint')} <Link to="/admin/tasks/new" className="text-cobalt hover:underline">{t('admin.newTask')}</Link>
              </p>
            </div>
          </section>

          <section className="card p-5 sm:p-6">
            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 mt-0.5 accent-cobalt" checked={published} onChange={(e) => setPublished(e.target.checked)} />
              <span>
                <span className="font-semibold text-sm">{t('assign.published')}</span>
                <span className="block text-[13px] text-ink-muted">{t('assign.publishedHint')}</span>
              </span>
            </label>
          </section>

          {error && <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <button type="submit" disabled={saving || !courseId} className="btn-primary">
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('common.save')}
            </button>
            <Link to={isEdit ? `/assignments/${assignmentId}` : `/courses/${courseId}`} className="btn-ghost">{t('form.cancel')}</Link>
            {isEdit && !isLab && (
              <button type="button" onClick={remove} className="btn-danger ml-auto"><Trash2 size={15} /> {t('assign.delete')}</button>
            )}
          </div>
        </form>
      </main>
      {gen && course?.subject_id && <GenerateModal courseId={course.id} subjectId={course.subject_id}
        onClose={() => setGen(false)}
        onDone={(made) => {
          setGen(false)
          qc.invalidateQueries({ queryKey: ['task-bank', courseId] })
          setTasks((p) => [...p, ...made.map((m) => ({ task_id: m.id, title: m.title, language: m.language, points: 10, variant_group: null, kind: m.kind }))])
        }} />}
    </div>
  )
}


const GEN_STAGES = ['subj.genTask', 'subj.genSolution', 'subj.genTests', 'subj.genCheck'] as const

/** The tutor writes new tasks for the course's subject: with tests (the AI's own solution must pass them) or a
 *  project handed in as a zip (rubric + a reference solution for the staff). They are added to this assignment. */
function GenerateModal({ courseId, subjectId, onClose, onDone }: {
  courseId: string; subjectId: string; onClose: () => void
  onDone: (made: { id: string; title: string; language: string; kind: string }[]) => void
}) {
  const { t, tError } = useLanguage()
  const { data: subject } = useQuery<SubjectDetail>({ queryKey: ['subject', subjectId], queryFn: () => subjectsApi.get(subjectId) })
  const [type, setType] = useState<'tests' | 'project'>('tests')
  const [language, setLanguage] = useState('')
  const [level, setLevel] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [topic, setTopic] = useState('')
  const [count, setCount] = useState(1)
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState(0)
  const [err, setErr] = useState('')
  useEffect(() => { if (subject && !language) setLanguage(subject.languages[0] ?? '') }, [subject]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!busy) return
    setStage(0)
    const id = setInterval(() => setStage((x) => Math.min(x + 1, GEN_STAGES.length - 1)), 10000)
    return () => clearInterval(id)
  }, [busy])
  const go = async () => {
    setBusy(true); setErr('')
    try {
      const r = await assignmentsApi.generateTasks(courseId, { language, level, topic, count, type })
      onDone(r.tasks)
    } catch (e: any) { setErr(tError(e.response?.data?.detail, 'subj.genFailed')) } finally { setBusy(false) }
  }
  return (
    <div className="fixed inset-0 z-50 bg-ink/50 flex items-start sm:items-center justify-center p-4 overflow-y-auto" role="dialog" aria-modal="true" aria-label={t('gen.open')}>
      <div className="card-stamp w-full max-w-lg p-5">
        <div className="flex items-center gap-2">
          <h2 className="font-extrabold text-lg flex-1 flex items-center gap-2"><Sparkles size={17} /> {t('gen.open')}</h2>
          <button className="btn-ghost btn-sm px-1.5" onClick={onClose} disabled={busy} aria-label={t('form.cancel')}><X size={16} /></button>
        </div>
        <p className="mt-1 text-[13px] text-ink-muted">{subject?.name}</p>
        <fieldset className="mt-4" disabled={busy}>
          <legend className="field-label">{t('gen.type')}</legend>
          <div className="grid sm:grid-cols-2 gap-2">
            {(['tests', 'project'] as const).map((x) => (
              <button key={x} type="button" onClick={() => setType(x)} aria-pressed={type === x}
                className={`rounded-lg border-2 px-3 py-2 text-left ${type === x ? 'border-ink bg-marker-soft/60' : 'border-line hover:border-ink-faint'}`}>
                <span className="block font-bold text-[13.5px]">{t(`gen.type.${x}` as any)}</span>
                <span className="block text-[12px] text-ink-muted">{t(`gen.type.${x}Hint` as any)}</span>
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className="mt-3" disabled={busy}>
          <legend className="field-label">{t('subj.language')}</legend>
          <div className="flex flex-wrap gap-1.5">
            {(subject?.languages ?? []).map((l) => (
              <button key={l} type="button" onClick={() => setLanguage(l)} aria-pressed={language === l}
                className={`${langClass(l)} h-8 px-2.5 rounded-lg border text-[12.5px] font-bold ${language === l ? 'bg-marker border-marker-deep/40 text-ink ring-2 ring-marker/40' : 'bg-surface border-line text-ink-muted hover:text-ink'}`}>
                {langInfo(l).label}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="mt-3 grid grid-cols-[1fr_6rem] gap-3">
          <fieldset disabled={busy}>
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
          <label>
            <span className="field-label">{t('gen.count')}</span>
            <select className="input h-8 py-0" value={count} disabled={busy} onChange={(e) => setCount(Number(e.target.value))}>
              {[1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        </div>
        <label className="mt-3 block">
          <span className="field-label">{t('subj.topic')}</span>
          <input className="input h-9" value={topic} maxLength={300} disabled={busy} onChange={(e) => setTopic(e.target.value)} placeholder={t('gen.topicPh')} />
        </label>
        {err && <p role="alert" className="mt-3 text-[13px] text-bad bg-bad-soft rounded-lg px-3 py-2">{err}</p>}
        <button type="button" className="btn-primary w-full mt-4" onClick={go} disabled={busy || !language}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {busy ? t(GEN_STAGES[stage]) : t('gen.go', { n: count })}
        </button>
        <p className="mt-2 text-[12px] text-ink-muted text-center">{busy ? t('gen.wait') : t('gen.note')}</p>
      </div>
    </div>
  )
}
