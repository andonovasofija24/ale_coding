import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FlaskConical, Loader2, RotateCcw, Sparkles } from 'lucide-react'
import { sessionsApi, tasksApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { AIPolicy, RunTestsResponse, Task } from '../types'
import { langClass, langInfo } from '../lib/languages'
import { loadRun, saveRun, StoredRun } from '../lib/testRun'
import { formatDateTime } from '../lib/time'
import AppHeader from '../components/AppHeader'
import LangChip from '../components/LangChip'
import Markdown from '../components/Markdown'
import ResultTable from '../components/ResultTable'
import TestResultsTable from '../components/TestResultsTable'
import DiagramEditor from '../components/DiagramEditor'
import { diagramKindOf } from '../lib/diagram'

/** All tests of a task on one wide page: every test with input, expected and actual output. Runs the code that was
 *  in the editor when the student came here; "Back to the code" returns to the editor with the same results. */
export default function TestsPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [params] = useSearchParams()
  const assignmentId = params.get('assignment')
  const { t, tError, lang } = useLanguage()
  const [run, setRun] = useState<StoredRun | null>(() => (taskId ? loadRun(taskId) : null))
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [explain, setExplain] = useState<string | null>(null)
  const [explaining, setExplaining] = useState(false)
  const { data: task } = useQuery<Task>({ queryKey: ['task', taskId], queryFn: () => tasksApi.get(taskId!) })
  const { data: policy } = useQuery<AIPolicy>({ queryKey: ['ai-policy', taskId], queryFn: () => tasksApi.aiPolicy(taskId!), retry: 0 })
  const back = `/tasks/${taskId}${assignmentId ? `?assignment=${assignmentId}` : ''}`

  const rerun = async () => {
    if (!taskId || !run) return
    setRunning(true); setError(''); setExplain(null)
    try {
      const results: RunTestsResponse = await sessionsApi.runTests(taskId, run.code)
      const next = { code: run.code, results, submit: null, at: Date.now() }
      saveRun(taskId, next); setRun(next)
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'task.runTestsError'))
    } finally { setRunning(false) }
  }

  const explainErrors = async () => {
    if (!taskId || !run?.results) return
    setExplaining(true)
    try {
      const errors = run.results.results.filter((r) => r.error).map((r) => r.error as string)
      setExplain((await sessionsApi.explainErrors(taskId, run.code, errors)).explanation)
    } catch (err: any) {
      setExplain(tError(err.response?.data?.detail, 'task.explainError'))
    } finally { setExplaining(false) }
  }

  if (!task) return <div className="flex items-center justify-center h-screen text-ink-muted"><Loader2 className="animate-spin" /></div>
  const tables = !!langInfo(task.language).tables
  const r = run?.results

  return (
    <div className={`${langClass(task.language)} min-h-screen bg-paper`}>
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <Link to={back} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {t('tests.backToCode')}
        </Link>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[16rem]">
            <p className="flex items-center gap-2 text-sm text-ink-muted"><LangChip lang={task.language} /> {task.title}</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight">{t('tests.title')}</h1>
            {run?.results && <p className="mt-1 text-[13px] text-ink-muted">{t('tests.ranAt', { when: formatDateTime(new Date(run.at).toISOString(), lang) })}</p>}
          </div>
          {run && (
            <button onClick={rerun} disabled={running} className="btn-secondary">
              {running ? <Loader2 size={15} className="animate-spin" /> : run.results ? <RotateCcw size={15} /> : <FlaskConical size={15} />}
              {run.results ? t('tests.rerun') : t('tests.runNow')}
            </button>
          )}
          <Link to={back} className="btn-primary">{t('tests.backToCode')}</Link>
        </div>

        {error && <p role="alert" className="mt-4 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}

        {run?.submit && !r && (
          <div className="mt-6 card px-5 py-4 text-sm">{run.submit.passed != null ? t('submit.testsPassed', { passed: run.submit.passed, total: run.submit.total ?? 0 }) : t('exam.resultsHidden')}</div>
        )}

        {r ? (
          <div className="mt-6 grid lg:grid-cols-[minmax(0,1fr)_20rem] gap-6 items-start">
            <div className="card p-4 sm:p-5 min-w-0">
              {running ? <div className="py-16 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
                : <TestResultsTable key={run!.at} results={r.results} passed={r.passed} total={r.total} tables={tables} />}
            </div>
            <aside className="space-y-4">
              <div className="card p-4">
                <h2 className="text-sm font-bold">{diagramKindOf(run!.code) ? t('tests.testedDiagram') : t('tests.testedCode')}</h2>
                {diagramKindOf(run!.code)
                  ? <div className="mt-2 h-80 rounded-lg border border-line overflow-hidden"><DiagramEditor code={run!.code} kind={diagramKindOf(run!.code)!} readOnly /></div>
                  : <pre className="mt-2 code-block max-h-[24rem] overflow-auto whitespace-pre text-[12px]">{run!.code}</pre>}
              </div>
              {policy?.mode === 'full' && r.results.some((x) => x.error) && (
                <div className="card p-4">
                  <button onClick={explainErrors} disabled={explaining} className="btn-secondary w-full">
                    {explaining ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                    {explaining ? t('task.analyzingErrors') : t('task.explainErrors')}
                  </button>
                  {explain && <div className="mt-3 note-md text-sm"><Markdown>{explain}</Markdown></div>}
                </div>
              )}
            </aside>
          </div>
        ) : !run?.submit && (
          <section className="mt-6">
            <div className="card px-6 py-10 text-center">
              <FlaskConical size={22} className="mx-auto text-ink-faint" />
              <p className="mt-2 font-semibold">{t('tests.notRunYet')}</p>
              <p className="mt-1 text-sm text-ink-muted">{run?.code ? t('tests.runNowHint') : t('tests.notRunHint')}</p>
              {run?.code && (
                <button onClick={rerun} disabled={running} className="btn-primary mt-4">
                  {running ? <Loader2 size={15} className="animate-spin" /> : <FlaskConical size={15} />} {t('tests.runNow')}
                </button>
              )}
            </div>
            {task.test_cases.length > 0 && (
              <>
                <h2 className="mt-8 panel-title">
                  {t('task.exampleTests')}
                  {!!task.hidden_tests && <span className="ml-2 font-normal text-ink-muted">{t('tests.plusHidden', { n: task.hidden_tests })}</span>}
                </h2>
                <div className="mt-3 grid md:grid-cols-2 gap-3">
                  {task.test_cases.map((tc, i) => (
                    <div key={tc.id} className="card p-4">
                      <p className="text-sm font-semibold">{t('task.example', { n: i + 1 })}</p>
                      {tc.type === 'diagram' ? <p className="mt-2 text-sm">{tc.expected_output}</p> : <>
                      {tc.test_code && <pre className="mt-2 code-block max-h-48 overflow-auto">{tc.test_code}</pre>}
                      {tc.stdin && <><p className="mt-2 text-xs text-ink-muted">{t('task.in')}</p><pre className="code-block">{tc.stdin}</pre></>}
                      <p className="mt-2 text-xs text-ink-muted">{tables ? t('task.expectedResult') : t('task.out')}</p>
                      {tables ? <ResultTable text={tc.expected_output} tone="ok" /> : <pre className="code-block text-ok">{tc.expected_output}</pre>}
                      </>}
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>
        )}
      </main>
    </div>
  )
}
