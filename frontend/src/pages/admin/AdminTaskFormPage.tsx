import { useState, useEffect, ReactNode } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import Markdown from '../../components/Markdown'
import { adminApi, subjectsApi } from '../../services/api'
import { RubricItem, SubjectSummary, TaskKind, TestCase } from '../../types'
import { Plus, Trash2, Save, Loader2, EyeOff, Wand2, CheckCircle2, XCircle, Code2, FileText, FolderArchive, ClipboardCheck, Languages, Upload, Download } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import AppHeader from '../../components/AppHeader'
import { defineAleTheme, editorTheme } from '../../components/editorTheme'
import { LANG_ORDER, langClass, langInfo } from '../../lib/languages'
import { WebEditor } from '../../components/WebWorkspace'
import DiagramEditor from '../../components/DiagramEditor'
import { parseDiagram } from '../../lib/diagram'
import { PenTool, ListPlus } from 'lucide-react'
import { DEFAULT_WEB_FILES, joinBundle } from '../../lib/web'
import { Sparkles, Image as ImageIcon } from 'lucide-react'

/** A web test whose first lines say "// visual: 90": compares screenshots with the model solution. */
const isVisual = (code: string) => /^\s*\/\/\s*visual\s*:/im.test(code)

interface TestCaseForm {
  id?: string
  type: 'code_sample' | 'stdin_stdout' | 'diagram'
  test_code: string
  stdin: string
  expected_output: string
  is_hidden: boolean
  order: number
  _new?: boolean
  _dirty?: boolean // existing test changed in the form, saved with PUT
}

const editorOptions = {
  fontSize: 13,
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  padding: { top: 10 },
  renderLineHighlight: 'none' as const,
  overviewRulerLanes: 0,
}

/** A form section: explanation on the left, fields on the right (stacked on small screens). */
function Section({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section className="grid md:grid-cols-[14rem_minmax(0,1fr)] gap-4 md:gap-8 py-8 border-b border-line last:border-0">
      <div>
        <h2 className="font-bold text-[15px]">{title}</h2>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-muted">{hint}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

export default function AdminTaskFormPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = !!taskId
  const { t, tError } = useLanguage()

  // Title and description in both languages; `contentLang` is the one the task was written in (the original).
  const [texts, setTexts] = useState<Record<'mk' | 'en', { title: string; description: string }>>({ mk: { title: '', description: '' }, en: { title: '', description: '' } })
  const [contentLang, setContentLang] = useState<'mk' | 'en'>('mk')
  const [langTab, setLangTab] = useState<'mk' | 'en'>('mk')
  const [translating, setTranslating] = useState(false)
  const [kind, setKind] = useState<TaskKind>('code')
  const [rubric, setRubric] = useState<RubricItem[]>([])
  const title = texts[langTab].title
  const description = texts[langTab].description
  const setTitle = (v: string) => setTexts((p) => ({ ...p, [langTab]: { ...p[langTab], title: v } }))
  const setDescription = (v: string) => setTexts((p) => ({ ...p, [langTab]: { ...p[langTab], description: v } }))
  const isCode = kind === 'code'
  const [descTab, setDescTab] = useState<'write' | 'preview'>('write')
  const [starterCode, setStarterCode] = useState('')
  const [modelSolution, setModelSolution] = useState('')
  const [language, setLanguage] = useState('cpp')
  const [isPublic, setIsPublic] = useState(true)
  const [subjectId, setSubjectId] = useState('')
  const { data: subj } = useQuery<{ subjects: SubjectSummary[] }>({ queryKey: ['subjects'], queryFn: subjectsApi.list })
  const [testCases, setTestCases] = useState<TestCaseForm[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  // "Fill expected outputs from the model solution": per-test result of running the solution
  const [filling, setFilling] = useState(false)
  const [fillResult, setFillResult] = useState<Record<number, { ok: boolean; changed: boolean; error?: string }>>({})
  const tables = !!langInfo(language).tables
  const web = !!langInfo(language).web
  const diagram = langInfo(language).diagram
  const [drawing, setDrawing] = useState(false)
  const [drawFile, setDrawFile] = useState<File | null>(null)
  const [suggesting, setSuggesting] = useState(false)
  const [notes, setNotes] = useState<Record<number, string>>({})  // AI test titles, by index
  // Which languages the code runner can actually run (others are shown but disabled)
  const { data: installed } = useQuery({ queryKey: ['runner-languages'], queryFn: adminApi.languages, staleTime: 60_000 })
  const isInstalled = (l: string) => !installed?.runner || installed.languages.includes(l)

  const { data: task, isLoading } = useQuery({
    queryKey: ['admin-task', taskId],
    queryFn: () => adminApi.getTask(taskId!),
    enabled: isEdit,
  })

  useEffect(() => {
    if (task) {
      const orig = (task.content_lang ?? 'en') as 'mk' | 'en'
      const other = orig === 'mk' ? 'en' : 'mk'
      const tr = task.translations?.[other] ?? { title: '', description: '' }
      setTexts({ [orig]: { title: task.title, description: task.description }, [other]: { title: tr.title ?? '', description: tr.description ?? '' } } as any)
      setContentLang(orig); setLangTab(orig)
      setKind((task.kind ?? 'code') as TaskKind); setRubric(task.rubric ?? [])
      setStarterCode(task.starter_code)
      setModelSolution(task.model_solution)
      setLanguage(task.language)
      setIsPublic(task.is_public ?? true)
      setSubjectId(task.subject_id ?? '')
      setTestCases(
        task.test_cases.map((tc: TestCase) => ({
          id: tc.id,
          type: tc.type,
          test_code: tc.test_code,
          stdin: tc.stdin,
          expected_output: tc.expected_output,
          is_hidden: tc.is_hidden ?? false,
          order: tc.order,
        }))
      )
    }
  }, [task])

  const addTestCase = () => {
    setTestCases((prev) => [
      ...prev,
      diagram
        ? { type: 'diagram', test_code: '{"check": "node", "name": ""}', stdin: '', expected_output: '', is_hidden: false, order: prev.length, _new: true }
        : { type: 'code_sample', test_code: '', stdin: '', expected_output: '', is_hidden: false, order: prev.length, _new: true },
    ])
  }

  // Diagrams: tests made from the model solution (one per class/entity, attribute, method, relationship)
  const addDiagramTests = (tests: { type: string; test_code: string; expected_output: string; is_hidden: boolean }[]) => {
    setTestCases((prev) => {
      const have = new Set(prev.map((x) => x.test_code.replace(/\s/g, '')))
      const fresh = tests.filter((x) => !have.has(x.test_code.replace(/\s/g, '')))
      return [...prev, ...fresh.map((x, i) => ({ type: 'diagram' as const, test_code: x.test_code, stdin: '', expected_output: x.expected_output,
        is_hidden: x.is_hidden, order: prev.length + i, _new: true }))]
    })
  }
  const testsFromSolution = async () => {
    setError('')
    try {
      addDiagramTests((await adminApi.diagramTests({ kind: diagram!, model_solution: modelSolution, lang: contentLang })).tests)
    } catch (err: any) { setError(tError(err.response?.data?.detail, 'form.suggestFailed')) }
  }
  const drawWithAI = async () => {
    if (parseDiagram(modelSolution, diagram!).nodes.length && !confirm(t('dg.redrawConfirm'))) return
    setDrawing(true); setError('')
    try {
      const r = await adminApi.diagramDraft({ kind: diagram!, description: texts[contentLang].description || description, lang: contentLang, file: drawFile })
      setModelSolution(r.model_solution)
      addDiagramTests(r.tests)
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'dg.drawFailed'))
    } finally { setDrawing(false) }
  }

  const removeTestCase = async (idx: number) => {
    const tc = testCases[idx]
    if (tc.id && isEdit) {
      // Existing tests are deleted on the server right away, so ask first.
      if (!confirm(t('form.deleteTestConfirm', { n: idx + 1 }))) return
      await adminApi.deleteTestCase(taskId!, tc.id)
      qc.invalidateQueries({ queryKey: ['admin-task', taskId] })
    }
    setTestCases((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateTestCase = (idx: number, field: keyof TestCaseForm, value: string | boolean | number) => {
    setTestCases((prev) => prev.map((tc, i) => (i === idx ? { ...tc, [field]: value, _dirty: !tc._new } : tc)))
  }

  // HTML/CSS: start from index.html + style.css + script.js
  useEffect(() => {
    if (!web) return
    if (!starterCode.trim()) setStarterCode(joinBundle(DEFAULT_WEB_FILES))
    if (!modelSolution.trim()) setModelSolution(joinBundle(DEFAULT_WEB_FILES))
  }, [web]) // eslint-disable-line react-hooks/exhaustive-deps

  const addVisualTest = () => setTestCases((prev) => [...prev,
    { type: 'code_sample', test_code: '// visual: 90', stdin: '', expected_output: '', is_hidden: false, order: prev.length, _new: true }])

  const suggest = async () => {
    setSuggesting(true); setError('')
    try {
      const { tests } = await adminApi.suggestTests({
        language, description: texts[contentLang].description || description, model_solution: modelSolution,
        test_cases: testCases.map((tc) => ({ type: tc.type, test_code: tc.test_code, stdin: tc.stdin, expected_output: tc.expected_output,
          is_hidden: tc.is_hidden, order: tc.order })),
      })
      const start = testCases.length
      setTestCases((prev) => [...prev, ...tests.map((x, i) => ({ type: x.type, test_code: x.test_code, stdin: x.stdin,
        expected_output: x.expected_output, is_hidden: x.is_hidden, order: prev.length + i, _new: true }))])
      setFillResult((prev) => {
        const next = { ...prev }
        tests.forEach((x, i) => { if (x.checked != null) next[start + i] = { ok: x.checked, changed: false, error: x.error } })
        return next
      })
      setNotes((prev) => { const next = { ...prev }; tests.forEach((x, i) => { if (x.title) next[start + i] = x.title }); return next })
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'form.suggestFailed'))
    } finally { setSuggesting(false) }
  }

  const fillFromSolution = async () => {
    setFilling(true); setFillResult({}); setError('')
    try {
      const payload = testCases.map((tc) => ({
        type: tables ? 'code_sample' : tc.type, test_code: tc.test_code, stdin: tc.stdin,
        expected_output: tc.expected_output, is_hidden: tc.is_hidden, order: tc.order,
      }))
      const { results } = await adminApi.runPreview(language, modelSolution, payload)
      const info: Record<number, { ok: boolean; changed: boolean; error?: string }> = {}
      setTestCases((prev) => prev.map((tc, i) => {
        const r = results[i]
        if (!r) return tc
        if (r.error) { info[i] = { ok: false, changed: false, error: r.error }; return tc }
        if ((web && isVisual(tc.test_code)) || diagram) { info[i] = { ok: r.passed, changed: false, error: r.passed ? undefined : r.actual_output }; return tc }  // nothing to fill
        const changed = r.actual_output.trim() !== tc.expected_output.trim()
        info[i] = { ok: true, changed }
        return changed ? { ...tc, expected_output: r.actual_output, _dirty: !tc._new } : tc
      }))
      setFillResult(info)
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'form.fillFailed'))
    } finally {
      setFilling(false)
    }
  }

  const other: 'mk' | 'en' = contentLang === 'mk' ? 'en' : 'mk'
  // Always: the original -> the other language; then show the translation to check.
  const translateNow = async () => {
    const src = texts[contentLang]
    if (!src.title.trim() && !src.description.trim()) { setLangTab(contentLang); setError(t('err.Nothing to translate')); return }
    if (texts[other].title.trim() && !confirm(t('form.translateReplace'))) return
    setTranslating(true); setError('')
    try {
      const r = await adminApi.translate({ title: src.title, description: src.description, source: contentLang, target: other })
      setTexts((p) => ({ ...p, [other]: { title: r.title, description: r.description } }))
      setLangTab(other)
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'form.translateFailed'))
    } finally { setTranslating(false) }
  }
  const common = () => ({
    title: texts[contentLang].title, description: texts[contentLang].description, content_lang: contentLang,
    translations: { [other]: texts[other] }, kind, rubric: isCode ? [] : rubric.filter((r) => r.title.trim()),
    subject_id: isEdit ? subjectId : (subjectId || null),
  })

  const handleSave = async () => {
    setError('')
    if (!texts[contentLang].title.trim()) { setLangTab(contentLang); setError(t('form.titleRequired')); return }
    setSaving(true)
    try {
      if (isEdit) {
        await adminApi.updateTask(taskId!, { ...common(), starter_code: starterCode, model_solution: modelSolution, language, is_public: isPublic })
        for (const tc of testCases) {
          const data = {
            type: tables ? 'code_sample' : tc.type, test_code: tc.test_code, stdin: tc.stdin,
            expected_output: tc.expected_output, is_hidden: tc.is_hidden, order: tc.order,
          }
          if (tc._new) await adminApi.addTestCase(taskId!, data)
          else if (tc._dirty && tc.id) await adminApi.updateTestCase(taskId!, tc.id, data)
        }
        qc.invalidateQueries({ queryKey: ['admin-task', taskId] })
      } else {
        await adminApi.createTask({
          ...common(), starter_code: starterCode, model_solution: modelSolution, language, is_public: isPublic && isCode,
          test_cases: (isCode ? testCases : []).map((tc) => ({
            type: tables ? 'code_sample' : tc.type, test_code: tc.test_code, stdin: tc.stdin,
            expected_output: tc.expected_output, is_hidden: tc.is_hidden, order: tc.order,
          })),
        })
      }
      qc.invalidateQueries({ queryKey: ['admin-tasks'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
      navigate('/admin/tasks')
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'form.saveFailed'))
    } finally {
      setSaving(false)
    }
  }

  if (isEdit && isLoading) {
    return (
      <div className="flex items-center justify-center h-screen text-ink-muted">
        <Loader2 className="animate-spin" size={22} />
      </div>
    )
  }

  return (
    <div className={`${langClass(language)} min-h-screen bg-paper`}>
      <AppHeader showAdminLink={false}>
        <nav className="hidden sm:flex items-center gap-2 text-sm text-ink-muted ml-2 min-w-0">
          <Link to="/admin/tasks" className="hover:text-ink">{t('admin.manageTasks')}</Link>
          <span>/</span>
          <span className="font-semibold text-ink truncate">{isEdit ? t('form.editTask') : t('form.newTask')}</span>
        </nav>
      </AppHeader>

      {/* Sticky save bar */}
      <div className="sticky top-0 z-20 bg-paper/90 backdrop-blur border-b border-line">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-3">
          <h1 className="font-bold truncate">{title || (isEdit ? t('form.editTask') : t('form.newTask'))}</h1>
          <div className="ml-auto flex items-center gap-2">
            {error && <span role="alert" className="text-bad text-sm hidden md:inline">{error}</span>}
            <Link to="/admin/tasks" className="btn-ghost">{t('form.cancel')}</Link>
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              {t('common.save')}
            </button>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
        {error && <p role="alert" className="md:hidden mt-4 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}

        <Section title={t('kind.title')} hint={t('kind.hint')}>
          <div className="grid sm:grid-cols-2 gap-2" role="radiogroup" aria-label={t('kind.title')}>
            {([['code', <Code2 size={16} />], ['document', <FileText size={16} />], ['project', <FolderArchive size={16} />], ['offline', <ClipboardCheck size={16} />]] as [TaskKind, JSX.Element][]).map(([k, icon]) => (
              <label key={k} className={`cursor-pointer rounded-lg border px-3.5 py-2.5 transition-colors ${kind === k ? 'border-ink bg-paper/60 ring-1 ring-ink' : 'border-line hover:border-ink-faint'}`}>
                <input type="radio" name="kind" className="sr-only" checked={kind === k} onChange={() => setKind(k)} />
                <span className="flex items-center gap-1.5 font-semibold text-sm">{icon} {t(`kind.${k}` as any)}</span>
                <span className="block mt-0.5 text-xs text-ink-muted leading-snug">{t(`kind.${k}.hint` as any)}</span>
              </label>
            ))}
          </div>
        </Section>

        <Section title={t('form.details')} hint={t('form.detailsHintLang')}>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <div className="inline-flex rounded-lg bg-paper border border-line p-0.5" role="tablist" aria-label={t('form.textLanguage')}>
              {(['mk', 'en'] as const).map((l) => (
                <button key={l} type="button" role="tab" aria-selected={langTab === l} onClick={() => setLangTab(l)}
                  className={`h-8 px-3 rounded-md text-sm font-semibold inline-flex items-center gap-1.5 ${langTab === l ? 'bg-surface text-ink shadow-[0_1px_2px_rgba(26,34,51,.12)]' : 'text-ink-muted hover:text-ink'}`}>
                  {l === 'mk' ? 'Македонски' : 'English'}
                  {l === contentLang ? <span className="text-[10px] font-bold uppercase text-ink-muted">{t('form.original')}</span>
                    : !texts[l].title.trim() && <span className="w-1.5 h-1.5 rounded-full bg-marker-deep" title={t('form.noTranslation')} />}
                </button>
              ))}
            </div>
            <label className="inline-flex items-center gap-2 text-[13px] text-ink-muted">
              {t('form.writtenIn')}
              <select value={contentLang} onChange={(e) => setContentLang(e.target.value as 'mk' | 'en')} className="input h-8 w-auto text-[13px]">
                <option value="mk">Македонски</option>
                <option value="en">English</option>
              </select>
            </label>
            <button type="button" onClick={translateNow} disabled={translating} className="btn-secondary btn-sm ml-auto">
              {translating ? <Loader2 size={14} className="animate-spin" /> : <Languages size={14} />}
              {t('form.translateInto', { lang: other === 'mk' ? 'македонски' : 'English' })}
            </button>
          </div>
          {langTab !== contentLang && <p className="-mt-2 mb-3 text-[12px] text-ink-muted">{t('form.translationHint')}</p>}
          <div className={`grid gap-4 ${isCode ? 'sm:grid-cols-[minmax(0,1fr)_10rem]' : ''}`}>
            <div>
              <label htmlFor="title" className="field-label">{t('form.title')}</label>
              <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} className="input" placeholder={t('form.titlePlaceholder')} />
            </div>
            {isCode && <div>
              <label htmlFor="lang" className="field-label">{t('form.language')}</label>
              <select id="lang" value={language} onChange={(e) => setLanguage(e.target.value)} className="input">
                {LANG_ORDER.map((l) => (
                  <option key={l} value={l} disabled={!isInstalled(l) && l !== language}>
                    {langInfo(l).label}{isInstalled(l) ? '' : ` — ${t('form.notInstalled')}`}
                  </option>
                ))}
              </select>
            </div>}
          </div>

          <div className="mt-5">
            <label htmlFor="subject" className="field-label">{t('bank.subject')}</label>
            <select id="subject" className="input" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
              <option value="">{t('bank.noSubject')}</option>
              {(subj?.subjects ?? []).map((x) => <option key={x.id} value={x.id}>{x.code} — {x.name}</option>)}
            </select>
            <p className="field-hint">{t('bank.subjectHint')}</p>
          </div>

          {isCode && <fieldset className="mt-5">
            <legend className="field-label">{t('form.visibility')}</legend>
            <div className="grid sm:grid-cols-2 gap-2">
              {[true, false].map((v) => (
                <label key={String(v)} className={`cursor-pointer rounded-lg border px-3.5 py-2.5 transition-colors ${
                  isPublic === v ? 'border-ink bg-paper/60 ring-1 ring-ink' : 'border-line hover:border-ink-faint'}`}>
                  <input type="radio" name="visibility" className="sr-only" checked={isPublic === v} onChange={() => setIsPublic(v)} />
                  <span className="block font-semibold text-sm">{v ? t('form.public') : t('form.courseOnly')}</span>
                  <span className="block mt-0.5 text-xs text-ink-muted leading-snug">{v ? t('form.publicHint') : t('form.courseOnlyHint')}</span>
                </label>
              ))}
            </div>
          </fieldset>}

          <div className="mt-5">
            <div className="flex items-end justify-between mb-1.5">
              <label htmlFor="desc" className="field-label mb-0">{t('form.description')}</label>
              <div className="inline-flex rounded-md bg-paper border border-line p-0.5 text-xs font-semibold">
                {(['write', 'preview'] as const).map((k) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setDescTab(k)}
                    className={`h-6 px-2.5 rounded ${descTab === k ? 'bg-surface text-ink shadow-[0_1px_2px_rgba(26,34,51,.12)]' : 'text-ink-muted hover:text-ink'}`}
                  >
                    {k === 'write' ? t('form.write') : t('form.preview')}
                  </button>
                ))}
              </div>
            </div>
            {descTab === 'write' ? (
              <textarea
                id="desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={12}
                className="input font-mono text-[13px]"
                placeholder={t('form.descriptionPlaceholder')}
              />
            ) : (
              <div className="card px-5 py-4 min-h-[16rem] task-description">
                {description ? <Markdown>{description}</Markdown> : <p className="text-ink-faint">{t('form.previewEmpty')}</p>}
              </div>
            )}
          </div>
        </Section>

        {!isCode && (
          <Section title={t('rubric.title')} hint={t('rubric.hint')}>
            <RubricEditor rubric={rubric} onChange={setRubric} />
          </Section>
        )}
        {(kind === 'document' || kind === 'project') && (
          <Section title={t('reference.title')} hint={t('reference.hint')}>
            {isEdit ? <ReferenceFile taskId={taskId!} file={task?.reference_file ?? null} /> : <p className="text-sm text-ink-muted">{t('reference.saveFirst')}</p>}
          </Section>
        )}

        {isCode && <>
        <Section title={diagram ? t('dg.starter') : t('form.starterCode')} hint={diagram ? t('dg.starterHint') : t('form.starterCodeHint')}>
          <div className="card overflow-hidden" style={{ height: web ? 280 : diagram ? 260 : 200 }}>
            {diagram ? <DiagramEditor code={starterCode} onChange={setStarterCode} kind={diagram} /> : web ? <WebEditor code={starterCode} onChange={setStarterCode} /> :
            <Editor language={langInfo(language).monaco} value={starterCode} onChange={(v) => setStarterCode(v || '')} options={editorOptions} beforeMount={defineAleTheme} theme={editorTheme(language)} loading={<span className="text-sm text-ink-muted">{t('common.loading')}</span>} />}
          </div>
        </Section>

        <Section title={t('form.modelSolution')} hint={diagram ? t('dg.solutionHint') : t('form.modelSolutionNote')}>
          {diagram && (
            <div className="mb-3 card p-3 flex flex-wrap items-center gap-2">
              <PenTool size={16} className="text-obj" />
              <span className="text-[13px] font-semibold">{t('dg.drawAI')}</span>
              <label className="btn-ghost btn-sm cursor-pointer">
                <input type="file" accept=".pdf,.png,.jpg,.jpeg" className="sr-only" onChange={(e) => setDrawFile(e.target.files?.[0] ?? null)} />
                <Upload size={14} /> {drawFile ? drawFile.name : t('dg.taskFile')}
              </label>
              {drawFile && <button className="text-ink-faint hover:text-bad text-xs" onClick={() => setDrawFile(null)}>✕</button>}
              <span className="flex-1" />
              <button className="btn-secondary btn-sm" disabled={drawing || (!drawFile && !(texts[contentLang].description || description).trim())} onClick={drawWithAI}>
                {drawing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} {drawing ? t('dg.drawing') : t('dg.draw')}
              </button>
              <p className="basis-full text-[12px] text-ink-muted">{t('dg.drawHint')}</p>
            </div>
          )}
          <div className="card overflow-hidden border-dashed" style={{ height: web ? 380 : diagram ? 460 : 320 }}>
            {diagram ? <DiagramEditor code={modelSolution} onChange={setModelSolution} kind={diagram} /> : web ? <WebEditor code={modelSolution} onChange={setModelSolution} /> :
            <Editor language={langInfo(language).monaco} value={modelSolution} onChange={(v) => setModelSolution(v || '')} options={editorOptions} beforeMount={defineAleTheme} theme={editorTheme(language)} loading={<span className="text-sm text-ink-muted">{t('common.loading')}</span>} />}
          </div>
        </Section>

        <Section title={t('form.testCases')} hint={`${t('form.testCasesNote')} ${capitalize(t(`how.${tables ? 'query' : 'function'}.${language}` as any))}${tables ? ' ' + t('form.sqlMarkers') : ''}`}>
          {testCases.length === 0 ? (
            <div className="card px-5 py-8 text-center">
              <p className="font-semibold text-sm">{t('form.noTests')}</p>
              <p className="mt-1 text-[13px] text-ink-muted">{t('form.noTestsHint')}</p>
            </div>
          ) : (
            <ol className="space-y-4">
              {testCases.map((tc, idx) => {
                return (
                  <li key={tc.id ?? `new-${idx}`} className={`card p-4 ${tc.is_hidden ? 'bg-paper/60' : ''}`}>
                    <div className="flex items-center gap-3 mb-4">
                      <span className="font-bold text-sm">{t('form.test', { n: idx + 1 })}</span>
                      {web && isVisual(tc.test_code) && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-marker-deep bg-marker-soft rounded-full px-2 py-0.5">
                          <ImageIcon size={12} /> {t('form.visualTest')}
                        </span>
                      )}
                      {notes[idx] && <span className="text-xs text-ink-muted truncate max-w-[16rem]" title={notes[idx]}>{notes[idx]}</span>}
                      {tc.is_hidden && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-ink-soft bg-line-soft rounded-full px-2 py-0.5">
                          <EyeOff size={12} /> {t('form.hidden')}
                        </span>
                      )}
                      {tc._new && <span className="text-xs font-semibold text-cobalt bg-cobalt-soft rounded-full px-2 py-0.5">{t('form.unsaved')}</span>}
                      {tc._dirty && <span className="text-xs font-semibold text-cobalt bg-cobalt-soft rounded-full px-2 py-0.5">{t('form.changed')}</span>}
                      <div className="ml-auto flex items-center gap-3">
                        <label className="flex items-center gap-1.5 text-[13px] text-ink-soft cursor-pointer">
                          <input
                            type="checkbox"
                            checked={tc.is_hidden}
                            onChange={(e) => updateTestCase(idx, 'is_hidden', e.target.checked)}
                            className="w-4 h-4 accent-cobalt"
                          />
                          {t('form.hiddenToggle')}
                        </label>
                        <button onClick={() => removeTestCase(idx)} className="btn-ghost btn-sm px-2 text-bad hover:text-bad hover:bg-bad-soft" aria-label={t('form.deleteTest')} title={t('form.deleteTest')}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {diagram && (
                        <div>
                          <label className="field-label">{t('dg.checkText')}</label>
                          <input className="input" value={tc.expected_output} onChange={(e) => updateTestCase(idx, 'expected_output', e.target.value)} />
                        </div>
                      )}
                      <div className={`grid gap-3 ${tables || web || diagram ? 'grid-cols-[7rem]' : 'sm:grid-cols-[minmax(0,1fr)_7rem]'}`}>
                        <div className={tables || web || diagram ? 'hidden' : ''}>
                          <label className="field-label">{t('form.type')}</label>
                          <select value={tc.type} onChange={(e) => updateTestCase(idx, 'type', e.target.value)} className="input">
                            <option value="code_sample">{t('form.typeCodeSample')}</option>
                            <option value="stdin_stdout">{t('form.typeStdin')}</option>
                          </select>
                        </div>
                        <div>
                          <label className="field-label">{t('form.order')}</label>
                          <input type="number" value={tc.order} onChange={(e) => updateTestCase(idx, 'order', parseInt(e.target.value))} className="input" />
                        </div>
                      </div>

                      {tables || tc.type === 'code_sample' ? (
                        <div>
                          <label className="field-label">{tables ? t('form.sqlData') : diagram ? t('dg.checkJson') : web ? t('form.snippetWeb') : t('form.snippet')}</label>
                          <textarea
                            value={tc.test_code}
                            onChange={(e) => updateTestCase(idx, 'test_code', e.target.value)}
                            rows={tables ? 7 : web ? 4 : diagram ? 2 : 3}
                            className="input font-mono text-[13px]"
                            placeholder={langInfo(language).snippetPlaceholder}
                          />
                        </div>
                      ) : (
                        <div>
                          <label className="field-label">{t('form.stdin')}</label>
                          <textarea value={tc.stdin} onChange={(e) => updateTestCase(idx, 'stdin', e.target.value)} rows={2} className="input font-mono text-[13px]" />
                        </div>
                      )}

                      {diagram ? null : web && isVisual(tc.test_code) ? (
                        <p className="text-[12.5px] text-ink-muted">{t('form.visualHint')}</p>
                      ) : <div>
                        <label className="field-label">{tables ? t('form.expectedTable') : t('form.expectedOutput')}</label>
                        <textarea value={tc.expected_output} onChange={(e) => updateTestCase(idx, 'expected_output', e.target.value)} rows={tables ? 4 : 2} className="input font-mono text-[13px]"
                          placeholder={tables ? 'ime | prosek\nАна | 9.5' : undefined} />
                      </div>}
                      {fillResult[idx] && (
                        <p className={`flex items-start gap-1.5 text-xs ${fillResult[idx].ok ? 'text-ok' : 'text-bad'}`}>
                          {fillResult[idx].ok ? <CheckCircle2 size={13} className="shrink-0 mt-px" /> : <XCircle size={13} className="shrink-0 mt-px" />}
                          {fillResult[idx].ok
                            ? (fillResult[idx].changed ? t('form.fillChanged') : t('form.fillSame'))
                            : <span className="font-mono whitespace-pre-wrap break-words">{t('form.fillError')} {fillResult[idx].error}</span>}
                        </p>
                      )}
                    </div>
                  </li>
                )
              })}
            </ol>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button onClick={addTestCase} className="btn-secondary">
              <Plus size={15} /> {t('form.addTest')}
            </button>
            <button onClick={fillFromSolution} disabled={filling || !modelSolution.trim() || testCases.length === 0} className="btn-ghost"
              title={t('form.fillHint')}>
              {filling ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />} {t('form.fill')}
            </button>
            {diagram && (
              <button onClick={testsFromSolution} disabled={!modelSolution.includes('"name"')} className="btn-ghost" title={t('dg.testsFromSolutionHint')}>
                <ListPlus size={15} /> {t('dg.testsFromSolution')}
              </button>
            )}
            {web && (
              <button onClick={addVisualTest} className="btn-ghost" title={t('form.addVisualHint')}>
                <ImageIcon size={15} /> {t('form.addVisual')}
              </button>
            )}
            <span className="flex-1" />
            {!diagram && <button onClick={suggest} disabled={suggesting || !(texts[contentLang].description || description).trim()} className="btn-secondary"
              title={t('form.suggestHint')}>
              {suggesting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {suggesting ? t('form.suggesting') : t('form.suggest')}
            </button>}
          </div>
        </Section>
        </>}
      </main>
    </div>
  )
}

/** Grading criteria: title + points each. The task's points in an assignment are split in the same proportion. */
function RubricEditor({ rubric, onChange }: { rubric: RubricItem[]; onChange: (r: RubricItem[]) => void }) {
  const { t } = useLanguage()
  const total = rubric.reduce((n, r) => n + (Number(r.points) || 0), 0)
  const set = (i: number, patch: Partial<RubricItem>) => onChange(rubric.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  return (
    <div>
      {rubric.length === 0 ? <p className="text-sm text-ink-muted">{t('rubric.empty')}</p> : (
        <ol className="space-y-2">
          {rubric.map((r, i) => (
            <li key={r.id} className="flex items-center gap-2">
              <span className="w-5 text-sm font-bold text-ink-muted">{i + 1}</span>
              <input className="input flex-1" value={r.title} maxLength={200} placeholder={t('rubric.criterionPlaceholder')}
                aria-label={t('rubric.criterion')} onChange={(e) => set(i, { title: e.target.value })} />
              <input type="number" min={0} max={1000} step={0.5} className="input w-24 text-right" value={r.points}
                aria-label={t('rubric.points')} onChange={(e) => set(i, { points: parseFloat(e.target.value) || 0 })} />
              <button type="button" onClick={() => onChange(rubric.filter((_, j) => j !== i))} className="btn-ghost btn-sm px-2 text-ink-muted hover:text-bad"
                aria-label={t('rubric.remove')}><Trash2 size={15} /></button>
            </li>
          ))}
        </ol>
      )}
      <div className="mt-3 flex items-center gap-3">
        <button type="button" className="btn-secondary btn-sm"
          onClick={() => onChange([...rubric, { id: `c${Date.now().toString(36)}`, title: '', points: 1 }])}>
          <Plus size={14} /> {t('rubric.add')}
        </button>
        {rubric.length > 0 && <span className="text-sm text-ink-muted tabular-nums">{t('rubric.total', { n: total })}</span>}
      </div>
    </div>
  )
}

/** The teacher's own solution file (PDF, document or zip) — visible only to staff while grading. */
function ReferenceFile({ taskId, file }: { taskId: string; file: { name: string; size: number } | null }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const upload = async (f?: File) => {
    if (!f) return
    setBusy(true); setMsg('')
    try { await adminApi.uploadReference(taskId, f); qc.invalidateQueries({ queryKey: ['admin-task', taskId] }) }
    catch (err: any) { setMsg(tError(err.response?.data?.detail, 'reference.failed')) }
    finally { setBusy(false) }
  }
  return (
    <div className="space-y-3">
      {file ? (
        <div className="card px-4 py-3 flex items-center gap-3">
          <FileText size={18} className="text-ink-muted" />
          <span className="flex-1 min-w-0 truncate text-sm font-medium">{file.name}</span>
          <span className="text-[12px] text-ink-muted tabular-nums">{Math.ceil(file.size / 1024)} KB</span>
          <button type="button" className="btn-ghost btn-sm" onClick={() => adminApi.downloadReference(taskId, file.name)}><Download size={14} /></button>
          <button type="button" className="btn-ghost btn-sm text-ink-muted hover:text-bad" aria-label={t('reference.remove')}
            onClick={async () => { await adminApi.deleteReference(taskId); qc.invalidateQueries({ queryKey: ['admin-task', taskId] }) }}><Trash2 size={14} /></button>
        </div>
      ) : <p className="text-sm text-ink-muted">{t('reference.none')}</p>}
      <label className="btn-secondary btn-sm cursor-pointer">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} {file ? t('reference.replace') : t('reference.upload')}
        <input type="file" className="sr-only" onChange={(e) => upload(e.target.files?.[0])} />
      </label>
      {msg && <p className="text-sm text-bad">{msg}</p>}
    </div>
  )
}
