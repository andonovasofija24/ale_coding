import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import { defineAleTheme, editorTheme } from '../components/editorTheme'
import LangChip from '../components/LangChip'
import { langClass, langInfo, taskKind } from '../lib/languages'
import Markdown from '../components/Markdown'
import { tasksApi, sessionsApi, assignmentsApi } from '../services/api'
import { Task, Session, AgentMessage, RunTestsResponse, Assignment, SubmitResult, AIPolicy } from '../types'
import { Deadline, Points, fmt } from '../components/course/bits'
import { countdown, useNow } from '../lib/time'
import StepsPanel from '../components/StepsPanel'
import AgentChat from '../components/AgentChat'
import TestsSummary from '../components/TestsSummary'
import { loadRun, saveRun } from '../lib/testRun'
import ResultTable from '../components/ResultTable'
import LanguageSwitcher from '../components/LanguageSwitcher'
import TestVisualizer from '../components/TestVisualizer'
import { WebEditor, WebPreview } from '../components/WebWorkspace'
import DiagramEditor from '../components/DiagramEditor'
import { DiagramUploadBar, useDiagramUpload } from '../components/DiagramUpload'
import { useDiagnostics, DiagnosticsBadge } from '../lib/diagnostics'
import Logo from '../components/Logo'
import EmptyState from '../components/EmptyState'
import { usePageTour } from '../components/Tour'
import RunConsole, { canRunWithInput } from '../components/RunConsole'
import { useLanguage } from '../i18n/LanguageContext'
import {
  ArrowLeft, Play, Check, Lightbulb, FlaskConical, Loader2, RotateCcw, Sparkles, Eye, Route, MessageSquareText, Cloud, CloudUpload, Info,
  Send, ClipboardList, Timer, BotOff, ShieldAlert, Wand2, TrendingUp, ListChecks, MonitorPlay, TerminalSquare, FileText,
} from 'lucide-react'

type RightTab = 'steps' | 'chat' | 'tests' | 'preview'
type SaveState = 'idle' | 'saving' | 'saved'

export default function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const qc = useQueryClient()
  const { t, tError } = useLanguage()
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [vizTest, setVizTest] = useState<{ tc: Task['test_cases'][number]; n: number } | null>(null)

  const [code, setCode] = useState<string>('')
  const [codeInitialized, setCodeInitialized] = useState(false)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [unread, setUnread] = useState(0)
  const [agentLoading, setAgentLoading] = useState(false)
  const [testsRunning, setTestsRunning] = useState(false)
  const [consoleOpen, setConsoleOpen] = useState(false)
  // the task tour (the first time a task is opened; replayed with the "Guide" button)
  usePageTour('task')
  const [testResults, setTestResults] = useState<RunTestsResponse | null>(null)
  const [testRunId, setTestRunId] = useState(0)
  const [errorExplanation, setErrorExplanation] = useState<string | null>(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [rightTab, setRightTab] = useState<RightTab>('steps')
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Opened from a course assignment (?assignment=<id>): show its deadline / points and allow submitting.
  const [searchParams] = useSearchParams()
  const assignmentId = searchParams.get('assignment')
  const { data: assignment } = useQuery<Assignment>({
    queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!), enabled: !!assignmentId, retry: 0,
  })
  const aTask = assignment?.tasks.find((x) => x.task_id === taskId)
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const lastSubmitted = useRef<string | null>(null)
  const [queuePos, setQueuePos] = useState<number | null>(null)

  // An active assignment may limit the AI tutor to a few hints or turn it off (e.g. during an exam).
  const { data: policy, refetch: refetchPolicy } = useQuery<AIPolicy>({
    queryKey: ['ai-policy', taskId], queryFn: () => tasksApi.aiPolicy(taskId!), enabled: !!taskId, retry: 0,
  })
  const restricted = !!policy && policy.mode !== 'full'
  const examRunning = !!assignment?.exam && assignment.my_role === 'student' && assignment.exam_state === 'running'
  const draftKey = `ale-draft:${taskId}`
  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)

  const { data: task } = useQuery<Task>({
    queryKey: ['task', taskId],
    queryFn: () => tasksApi.get(taskId!),
  })

  const { data: session, isLoading: sessionLoading } = useQuery<Session | null>({
    queryKey: ['session', taskId],
    queryFn: () => sessionsApi.getForTask(taskId!),
    enabled: !!taskId,
  })

  // Wait for BOTH the task and the session query: if the task arrived first, the editor would start from the
  // starter code and "Run tests" would test that instead of the student's saved code.
  useEffect(() => {
    if (!codeInitialized && task && !sessionLoading) {
      let draft: string | null = null
      try { draft = localStorage.getItem(draftKey) } catch { /* storage unavailable */ }
      const initial = session?.current_code || draft || task.starter_code || ''
      setCode(initial)
      setCodeInitialized(true)
      const last = loadRun(task.id)  // coming back from the tests page: show the same results again
      if (last && last.code === initial) { setTestResults(last.results); setSubmitResult(last.submit) }
    }
  }, [session, task, sessionLoading, codeInitialized, draftKey])

  // Without the step-by-step tutor there is no session to save into, so the code is kept in this browser.
  useEffect(() => {
    if (!codeInitialized || session) return
    const id = setTimeout(() => { try { localStorage.setItem(draftKey, code) } catch { /* ignore */ } }, 800)
    return () => clearTimeout(id)
  }, [code, codeInitialized, session, draftKey])

  useEffect(() => { if (restricted) setRightTab((tab) => (tab === 'steps' ? 'tests' : tab)) }, [restricted])
  // HTML/CSS tasks open with the live preview
  const isWeb = task?.language === 'web'
  const isDiagram = task?.language === 'uml' || task?.language === 'er'
  // diagram tasks: a picture / PDF of the student's own drawing can be read into the editor
  const upload = useDiagramUpload(taskId, (diagram) => handleCodeChange(diagram))
  useEffect(() => { if (isWeb) setRightTab('preview') }, [isWeb])

  // Compiler errors and warnings underlined in the editor while typing (never for HTML/CSS: the editor checks those)
  const diagnostics = useDiagnostics(taskId, code, codeInitialized && !!task && !isWeb && !isDiagram && policy?.editor_checks !== false,
    editorRef, monacoRef)

  // Exam signals for the teacher: leaving the page and coming back. Information only, never a verdict.
  useEffect(() => {
    if (!examRunning || !assignmentId) return
    const hidden = () => { if (document.visibilityState === 'hidden') assignmentsApi.event(assignmentId, 'blur', taskId) }
    const back = () => { if (document.visibilityState === 'visible') assignmentsApi.event(assignmentId, 'focus', taskId) }
    document.addEventListener('visibilitychange', hidden)
    document.addEventListener('visibilitychange', back)
    return () => { document.removeEventListener('visibilitychange', hidden); document.removeEventListener('visibilitychange', back) }
  }, [examRunning, assignmentId, taskId])

  const onEditorMount = (editor: any, monaco?: any) => {
    editorRef.current = editor
    monacoRef.current = monaco
    editor.onDidPaste((e: any) => {
      const text: string = editor.getModel()?.getValueInRange(e.range) ?? ''
      if (text.length >= 200 && examRunningRef.current && assignmentId) {
        assignmentsApi.event(assignmentId, 'paste', taskId, `${text.length} chars, ${text.split('\n').length} lines`)
      }
    })
  }
  const examRunningRef = useRef(false)
  examRunningRef.current = examRunning


  // Unread tutor notes are counted only while the tutor tab is not visible.
  useEffect(() => {
    if (rightTab === 'chat') setUnread(0)
  }, [rightTab])

  const pushMessage = (m: Omit<AgentMessage, 'timestamp'>) => {
    setMessages((prev) => [...prev, { ...m, timestamp: new Date() }])
    if (m.role === 'assistant') setUnread((u) => u + 1)
  }

  const refreshProgress = () => qc.invalidateQueries({ queryKey: ['my-sessions'] })

  const startSession = useMutation({
    // Start from what is already in the editor, so code typed before pressing "Start session" is kept.
    mutationFn: () => sessionsApi.start(taskId!, code),
    onMutate: () => setSessionError(null),
    onError: (err: any) => setSessionError(tError(err.response?.data?.detail, 'task.sessionError')),
    onSuccess: (newSession: Session) => {
      qc.setQueryData(['session', taskId], newSession)
      setCode(newSession.current_code || task?.starter_code || '')
      setCodeInitialized(true)
      setRightTab('steps')
      refreshProgress()
    },
  })

  const newSession = useMutation({
    mutationFn: () => sessionsApi.startNew(taskId!),
    onMutate: () => setSessionError(null),
    onError: (err: any) => setSessionError(tError(err.response?.data?.detail, 'task.sessionError')),
    onSuccess: (fresh: Session) => {
      qc.setQueryData(['session', taskId], fresh)
      setCode(fresh.current_code || task?.starter_code || '')
      setCodeInitialized(true)
      setTestResults(null)
      setErrorExplanation(null)
      setMessages([])
      setUnread(0)
      setRightTab('steps')
      refreshProgress()
    },
  })

  // "Write another solution": a new session that follows one of the offered approaches, from the starter code
  const altSession = useMutation({
    mutationFn: (approach: string) => sessionsApi.startApproach(taskId!, approach),
    onMutate: () => setSessionError(null),
    onError: (err: any) => setSessionError(tError(err.response?.data?.detail, 'task.sessionError')),
    onSuccess: (fresh: Session) => {
      qc.setQueryData(['session', taskId], fresh)
      setCode(fresh.current_code || task?.starter_code || '')
      setCodeInitialized(true)
      setTestResults(null)
      setErrorExplanation(null)
      setMessages([])
      setRightTab('steps')
      refreshProgress()
    },
  })

  const handleCodeChange = useCallback((val: string | undefined) => {
    const v = val ?? ''
    setCode(v)
    if (session) {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      setSaveState('saving')
      saveTimer.current = setTimeout(() => {
        sessionsApi.saveCode(session.id, v).then(() => setSaveState('saved')).catch(() => setSaveState('idle'))
      }, 1500)
    }
  }, [session])

  const handleCheckStep = async () => {
    if (!session) return
    setAgentLoading(true)
    setRightTab('chat')
    pushMessage({ role: 'user', kind: 'action', content: t('task.checkingStep', { n: session.current_step + 1 }) })
    try {
      const result = await sessionsApi.checkStep(session.id, code)
      pushMessage({ role: 'assistant', kind: result.passed ? 'pass' : 'fail', content: result.feedback })
      if (result.next_step) {
        const next = result.next_step
        pushMessage({
          role: 'assistant',
          kind: 'step',
          title: t('task.nextStepIntro', { n: next.step_number + 1, title: next.title }),
          content: next.description + (next.why ? `\n\n**${t('steps.why')}** ${next.why}` : ''),
        })
      } else if (result.all_steps_completed) {
        const alts = result.alternatives ?? []
        pushMessage({ role: 'assistant', kind: 'done', content: t('steps.allDoneHint') + (alts.length
          ? `\n\n**${t('alt.title', { n: alts.length })}**\n${alts.map((a: { title: string; idea: string }) => `- **${a.title}** — ${a.idea}`).join('\n')}\n\n${t('alt.inSteps')}`
          : '') })
        if (alts.length) setRightTab('steps')
      }
      if (result.passed) {
        qc.invalidateQueries({ queryKey: ['session', taskId] })
        refreshProgress()
      }
    } catch (err: any) {
      pushMessage({ role: 'assistant', kind: 'error', content: tError(err.response?.data?.detail, 'task.errorCheckingStep') })
    } finally {
      setAgentLoading(false)
    }
  }

  // Hints-only mode: a limited number of hints for the whole task, without a tutor session.
  const handleTaskHint = async () => {
    if (!taskId) return
    setAgentLoading(true)
    setRightTab('chat')
    pushMessage({ role: 'user', kind: 'action', content: t('task.askHint') })
    try {
      const r = await tasksApi.hint(taskId, code)
      pushMessage({ role: 'assistant', kind: 'hint', content: r.hint })
    } catch (err: any) {
      pushMessage({ role: 'assistant', kind: 'error', content: tError(err.response?.data?.detail, 'task.hintError') })
    } finally {
      setAgentLoading(false)
      refetchPolicy()
    }
  }

  const handleHint = async () => {
    if (!session) return
    setAgentLoading(true)
    setRightTab('chat')
    pushMessage({ role: 'user', kind: 'action', content: t('task.askHint') })
    try {
      const result = await sessionsApi.getHint(session.id, code)
      pushMessage({ role: 'assistant', kind: 'hint', content: result.hint })
    } catch (err: any) {
      pushMessage({ role: 'assistant', kind: 'error', content: tError(err.response?.data?.detail, 'task.hintError') })
    } finally {
      setAgentLoading(false)
    }
  }

  const handleRunTests = async () => {
    if (!taskId) return
    setTestsRunning(true)
    setRightTab('tests')
    setErrorExplanation(null)
    try {
      const results = await sessionsApi.runTests(taskId, code)
      setTestResults(results)
      setSubmitResult(null)
      setTestRunId((n) => n + 1)
      saveRun(taskId, { code, results, submit: null, at: Date.now() })
    } catch (err: any) {
      console.error('Run tests error', err)
      setTestResults(null)
      setErrorExplanation(tError(err.response?.data?.detail, 'task.runTestsError'))
    } finally {
      setTestsRunning(false)
    }
  }

  const handleSubmit = async (auto = false) => {
    if (!assignmentId || !taskId) return
    if (!auto && !confirm(t('submit.confirm'))) return
    setSubmitting(true); setSubmitError(null); setSubmitResult(null); setErrorExplanation(null)
    setRightTab('tests')
    const submitted = code
    try {
      let r: SubmitResult = await assignmentsApi.submit(assignmentId, taskId, submitted, upload.uploadId)
      lastSubmitted.current = submitted
      // Busy (e.g. a whole exam submitting at once): the submission is saved and waits in the queue — keep asking.
      while (r.status === 'pending' || r.status === 'running') {
        setQueuePos(r.queue_position ?? 0)
        await new Promise((ok) => setTimeout(ok, 1500))
        r = await assignmentsApi.result(r.submission_id)
      }
      setQueuePos(null)
      if (r.status === 'error') { setSubmitError(t('submit.queueError')); return }
      setSubmitResult(r)
      saveRun(taskId, { code: submitted, results: r.results.length ? { results: r.results, passed: r.passed ?? 0, total: r.total ?? 0,
        failed: (r.total ?? 0) - (r.passed ?? 0) } : null, submit: r, at: Date.now() })
      if (r.results.length > 0) {
        setTestResults({ results: r.results, passed: r.passed ?? 0, total: r.total ?? 0, failed: (r.total ?? 0) - (r.passed ?? 0) })
        setTestRunId((n) => n + 1)
      } else {
        setTestResults(null)
      }
      qc.invalidateQueries({ queryKey: ['assignment', assignmentId] })
    } catch (err: any) {
      setSubmitError(tError(err.response?.data?.detail, 'submit.failed'))
    } finally {
      setSubmitting(false)
      setQueuePos(null)
    }
  }

  // Suggestions for a solution that already passes every test (limited per task in "hints" mode).
  const handleImprove = async () => {
    if (!taskId) return
    setAgentLoading(true)
    setRightTab('chat')
    pushMessage({ role: 'user', kind: 'action', content: t('improve.ask') })
    try {
      const r = await tasksApi.improve(taskId, code)
      pushMessage({ role: 'assistant', kind: 'note', title: t('improve.title'), content: r.suggestions })
    } catch (err: any) {
      pushMessage({ role: 'assistant', kind: 'error', content: tError(err.response?.data?.detail, 'improve.failed') })
    } finally {
      setAgentLoading(false)
      refetchPolicy()
    }
  }

  const handleExplainErrors = async () => {
    if (!taskId || !testResults) return
    const errors = testResults.results.filter((r) => r.error).map((r) => r.error as string)
    if (errors.length === 0) return
    setExplainLoading(true)
    try {
      const res = await sessionsApi.explainErrors(taskId, code, errors)
      setErrorExplanation(res.explanation)
    } catch (err: any) {
      console.error('Explain errors failed', err)
      setErrorExplanation(tError(err.response?.data?.detail, 'task.explainError'))
    } finally {
      setExplainLoading(false)
    }
  }

  // The exam closes at the personal deadline: the last changes are handed in automatically just before.
  const offset = assignment?.server_time ? new Date(assignment.server_time).getTime() - Date.now() : 0
  const examNow = useNow(examRunning ? 1000 : 60_000) + offset
  const examEnds = examRunning && assignment?.attempt?.ends_at ? new Date(assignment.attempt.ends_at).getTime() : null
  useEffect(() => {
    if (!examEnds || !aTask) return
    const left = examEnds - examNow
    if (left <= 0) { qc.invalidateQueries({ queryKey: ['assignment', assignmentId] }); return }
    if (left < 10_000 && !submitting && codeInitialized && code !== (lastSubmitted.current ?? task?.starter_code ?? '')) {
      lastSubmitted.current = code
      handleSubmit(true)
    }
  }, [examNow]) // eslint-disable-line react-hooks/exhaustive-deps

  const activeStep = session?.steps.find((s) => s.step_number === session.current_step && s.status === 'active')
  const sessionCompleted = session?.status === 'completed'
  const busy = agentLoading || testsRunning || submitting

  if (!task) {
    return (
      <div className="flex items-center justify-center h-screen text-ink-muted gap-2">
        <Loader2 className="animate-spin" size={20} /> {t('task.loading')}
      </div>
    )
  }

  const info = langInfo(task.language)
  const kind = taskKind(task.test_cases, task.language)
  const tables = !!info.tables
  const fileName = info.file(kind)

  const allTabs: { key: RightTab; icon: JSX.Element; label: string; badge?: string; badgeTone?: string }[] = [
    ...(info.web ? [{ key: 'preview' as RightTab, icon: <MonitorPlay size={15} />, label: t('web.preview') }] : []),
    { key: 'steps', icon: <Route size={15} />, label: t('task.tabSteps') },
    {
      key: 'chat', icon: <MessageSquareText size={15} />, label: t('task.tabFeedback'),
      badge: unread > 0 && rightTab !== 'chat' ? String(unread) : undefined, badgeTone: 'bg-cobalt text-white',
    },
    {
      key: 'tests', icon: <FlaskConical size={15} />, label: t('task.tabTests'),
      badge: testResults ? `${testResults.passed}/${testResults.total}` : undefined,
      badgeTone: testResults && testResults.passed === testResults.total ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad',
    },
  ]
  const testsUrl = `/tasks/${taskId}/tests${assignmentId ? `?assignment=${assignmentId}` : ''}`
  const canImprove = !!policy && policy.mode !== 'off' && (policy.mode === 'full' || (policy.improve_left ?? 0) > 0)
  const tabs = allTabs.filter((tb) => !restricted || tb.key === 'tests' || tb.key === 'preview' || (tb.key === 'chat' && policy?.mode === 'hints'))
  // "All tests" page: it shows the last results of exactly this code, or offers to run the tests on it
  const openTests = () => {
    if (!taskId) return
    const last = loadRun(taskId)
    saveRun(taskId, last && last.code === code ? last : { code, results: null, submit: null, at: Date.now() })
  }
  const showSession = !restricted

  return (
    <div className={`${langClass(task.language)} flex flex-col h-screen bg-paper overflow-hidden`}>
      {vizTest && taskId && (
        <TestVisualizer taskId={taskId} testCase={vizTest.tc} testNumber={vizTest.n} onClose={() => setVizTest(null)} tables={tables} />
      )}

      {/* Top bar */}
      <header className="h-14 bg-surface border-b border-line px-3 sm:px-4 flex items-center gap-3 shrink-0">
        <Link to={assignmentId ? `/assignments/${assignmentId}` : task.subject_id ? `/subjects/${task.subject_id}` : '/courses'} className="btn-ghost btn-sm px-2"
          aria-label={assignmentId ? t('submit.backToAssignment') : t('task.backToTasks')} title={assignmentId ? t('submit.backToAssignment') : t('task.backToTasks')}>
          <ArrowLeft size={18} />
        </Link>
        <Link to="/courses" className="hidden md:block" aria-hidden tabIndex={-1}><Logo /></Link>
        <span className="hidden md:block w-px h-6 bg-line" />
        <h1 className="font-bold text-[15px] truncate">{task.title}</h1>
        <span className="hidden sm:inline-flex"><LangChip lang={task.language} /></span>

        <div className="ml-auto flex items-center gap-2">
          {sessionCompleted ? (
            <span className="hidden sm:inline-flex items-center gap-1 text-xs font-bold text-ok bg-ok-soft rounded-full px-2.5 py-1">
              <Check size={13} strokeWidth={3} /> {t('task.completed')}
            </span>
          ) : session ? (
            <span className="hidden sm:inline text-xs font-semibold text-ink-soft">
              <span className="marker">{t('steps.step', { n: session.current_step + 1 })}</span>
            </span>
          ) : null}
          <LanguageSwitcher />
          {session && showSession && (
            <button
              onClick={() => { if (confirm(t('task.newSessionConfirm'))) newSession.mutate() }}
              disabled={newSession.isPending}
              className="btn-ghost btn-sm"
              title={t('task.newSessionTitle')}
            >
              {newSession.isPending ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
              <span className="hidden lg:inline">{t('task.newSession')}</span>
            </button>
          )}
        </div>
      </header>

      {assignment && aTask && (
        <AssignmentBar a={assignment} points={aTask.points} best={aTask.my_submissions ? aTask.my_score ?? 0 : null}
          submissions={aTask.my_submissions ?? 0} onSubmit={() => handleSubmit()} submitting={submitting}
          examEnds={examEnds} examNow={examNow} />
      )}
      {restricted && policy && <PolicyBar policy={policy} />}

      {/* Workspace: task | editor | guidance */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden gap-px bg-line">
        {/* Left: task */}
        <section className="lg:w-[22rem] shrink-0 bg-surface flex flex-col lg:overflow-hidden" aria-label={t('task.description')}>
          <div className="flex-1 lg:overflow-y-auto px-5 py-5" data-tour="task-description">
            <h2 className="panel-title mb-3 flex items-center gap-2"><FileText size={15} className="text-cobalt" /> {t('task.description')}</h2>
            <div className="task-description">
              <Markdown>{task.description}</Markdown>
            </div>
          </div>

          {/* How the student's code is run — differs per language and task kind */}
          <div className="border-t border-line px-5 py-3.5 flex gap-2.5 text-[13px] leading-relaxed text-ink-soft">
            <Info size={15} className="shrink-0 mt-0.5 text-marker-deep" />
            <p>
              <span className="font-semibold text-ink">{t('how.title')}</span>{' '}
              {t(`how.${kind}.${task.language}` as any)}
            </p>
          </div>

          {task.test_cases.length > 0 && (
            <div className="border-t-2 border-line px-5 py-4 lg:max-h-[45%] lg:overflow-y-auto bg-paper/40" data-tour="task-examples">
              <div className="flex items-center justify-between mb-3 gap-2">
                <h2 className="panel-title">{t('task.exampleTests')}</h2>
                <Link to={testsUrl} onClick={openTests} className="text-[12.5px] font-semibold text-cobalt hover:underline whitespace-nowrap">{t('tests.viewAll')} →</Link>
              </div>
              <div className="space-y-3">
                {task.test_cases.map((tc, i) => (
                  <div key={tc.id} className="rounded-lg bg-surface border border-line-soft p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[13px] font-semibold">{t('task.example', { n: i + 1 })}</span>
                      {!restricted && !info.web && !info.diagram && !['git', 'dockerfile', 'yaml', 'terraform'].includes(task.language) && (
                        <button onClick={() => setVizTest({ tc, n: i + 1 })} className="btn-secondary btn-sm h-7 px-2 text-xs">
                          <Eye size={13} /> {t('viz.button')}
                        </button>
                      )}
                    </div>
                    {tc.type === 'diagram' ? <p className="text-[13px] text-ink">{tc.expected_output}</p> : <>
                    {tc.test_code && tables && <p className="text-xs text-ink-muted mb-1">{t('task.testData')}</p>}
                    {tc.test_code && <pre className={`code-block ${tables ? 'max-h-40 overflow-auto' : ''}`}>{tc.test_code}</pre>}
                    {tc.stdin && (
                      <div className="mt-2">
                        <p className="text-xs text-ink-muted mb-1">{t('task.in')}</p>
                        <pre className="code-block">{tc.stdin}</pre>
                      </div>
                    )}
                    {tables ? (
                      <div className="mt-2 text-xs">
                        <p className="text-ink-muted mb-1">{t('task.expectedResult')}</p>
                        <ResultTable text={tc.expected_output} tone="ok" />
                      </div>
                    ) : (
                      <div className="mt-2 flex gap-2 items-start text-xs">
                        <span className="text-ink-muted pt-0.5 shrink-0">{t('task.out')}</span>
                        <pre className="font-mono text-[12.5px] text-ok whitespace-pre-wrap">{tc.expected_output}</pre>
                      </div>
                    )}
                    </>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Center: editor */}
        <section className="flex-1 min-w-0 bg-surface flex flex-col min-h-[60vh] lg:min-h-0" aria-label={fileName} data-tour="task-editor">
          <div className="h-10 px-4 border-b border-line-soft flex items-center justify-between shrink-0">
            <span className="font-mono text-[13px] font-medium text-ink-soft flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-marker" aria-hidden />
              {info.web ? 'index.html · style.css · script.js' : info.diagram ? t(`dg.title.${info.diagram}` as any) : fileName}
            </span>
            <span className="flex items-center gap-3 text-xs text-ink-muted" aria-live="polite">
              <DiagnosticsBadge d={diagnostics} editor={editorRef} />
              <span className="flex items-center gap-1.5">
              {saveState === 'saving' ? (
                <><CloudUpload size={14} /> {t('task.saving')}</>
              ) : saveState === 'saved' ? (
                <><Cloud size={14} className="text-ok" /> {t('task.autoSaved')}</>
              ) : session ? (
                <><Cloud size={14} /> {t('task.autoSaveOn')}</>
              ) : restricted ? (
                t('task.savedInBrowser')
              ) : (
                t('task.notSavedYet')
              )}
              </span>
            </span>
          </div>

          <div className="flex-1 min-h-0">
            {info.diagram ? (
              <div className="h-full flex flex-col">
                <DiagramUploadBar u={upload} hasDiagram={code.includes('"name"')} />
                <div className="flex-1 min-h-[28rem]"><DiagramEditor code={code} onChange={handleCodeChange} kind={info.diagram} /></div>
              </div>
            ) : info.web ? <WebEditor code={code} onChange={handleCodeChange} onMount={onEditorMount} /> : <Editor
              language={info.monaco}
              value={code}
              onChange={handleCodeChange}
              beforeMount={defineAleTheme}
              onMount={onEditorMount}
              theme={editorTheme(task.language)}
              loading={<span className="text-sm text-ink-muted">{t('common.loading')}</span>}
              options={{
                fontSize: 14,
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                fontLigatures: true,
                lineHeight: 22,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                tabSize: 4,
                automaticLayout: true,
                padding: { top: 16, bottom: 16 },
                renderLineHighlight: 'all',
                overviewRulerLanes: 0,
                scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
              }}
            />}
          </div>

          {consoleOpen && canRunWithInput(task.language, info.web, info.diagram) && (
            <RunConsole taskId={task.id} code={code} functionTask={kind === 'function'} onClose={() => setConsoleOpen(false)} />
          )}

          {/* Action bar */}
          <div className="border-t border-line px-3 sm:px-4 py-3 flex flex-wrap items-center gap-2 shrink-0 bg-surface">
            <button data-tour="task-tests" onClick={handleRunTests} disabled={busy || (!session && !restricted)} className="btn-secondary"
              title={!session && !restricted ? t('task.startFirst') : undefined}>
              {testsRunning ? <Loader2 size={15} className="animate-spin" /> : <FlaskConical size={15} />}
              {t('task.runAllTests')}
            </button>
            <Link to={testsUrl} onClick={openTests} className="btn-ghost" title={t('tests.viewAllHint')}>
              <ListChecks size={15} /> <span className="hidden sm:inline">{t('tests.viewAll')}</span>
            </Link>
            {canRunWithInput(task.language, info.web, info.diagram) && (
              <button data-tour="task-run" onClick={() => setConsoleOpen((v) => !v)} className={`btn-ghost ${consoleOpen ? 'text-marker-deep bg-marker-soft' : ''}`}
                aria-pressed={consoleOpen} title={t('run.hint')}>
                <TerminalSquare size={15} /> <span className="hidden xl:inline">{t('run.open')}</span>
              </button>
            )}

            <div className="ml-auto flex items-center gap-2">
              {sessionError && <span role="alert" className="text-bad text-xs max-w-[16rem]">{sessionError}</span>}
              {policy?.mode === 'hints' && (
                <button onClick={handleTaskHint} disabled={busy || !policy.hints_left} className="btn-secondary">
                  <Lightbulb size={15} /> {t('task.hint')}
                  <span className="text-[11px] font-bold rounded-full bg-marker-soft text-marker-deep px-1.5 py-0.5 tabular-nums">{policy.hints_left}</span>
                </button>
              )}
              {showSession && !session && !sessionLoading && (
                <button data-tour="task-start" onClick={() => startSession.mutate()} disabled={startSession.isPending} className="btn-primary btn-lg">
                  {startSession.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                  {startSession.isPending ? t('task.preparingFirstStep') : t('task.startSession')}
                </button>
              )}
              {showSession && session && !sessionCompleted && (
                <>
                  <button onClick={handleHint} disabled={busy} className="btn-secondary">
                    <Lightbulb size={15} /> {t('task.hint')}
                  </button>
                  <button onClick={handleCheckStep} disabled={busy} className="btn-primary">
                    {agentLoading ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} strokeWidth={3} />}
                    {t('task.checkStep')}
                  </button>
                </>
              )}
            </div>
          </div>
        </section>

        {/* Right: guidance */}
        <aside className="lg:w-[24rem] shrink-0 bg-surface flex flex-col lg:overflow-hidden min-h-[24rem] lg:min-h-0">
          <div role="tablist" data-tour="task-tabs" className="flex gap-1 p-1.5 m-3 mb-0 rounded-lg bg-paper border-2 border-line shrink-0">
            {tabs.map((tab) => {
              const active = rightTab === tab.key
              return (
                <button
                  key={tab.key}
                  role="tab"
                  aria-selected={active}
                  onClick={() => setRightTab(tab.key)}
                  className={`flex-1 h-8 rounded-md flex items-center justify-center gap-1.5 text-[13px] font-semibold transition-colors ${
                    active ? 'bg-surface text-ink shadow-[0_1px_2px_rgba(26,34,51,.12)]' : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  {tab.icon}
                  <span className="truncate">{tab.label}</span>
                  {tab.badge && (
                    <span className={`text-[11px] font-bold leading-none rounded-full px-1.5 py-0.5 tabular-nums ${tab.badgeTone}`}>
                      {tab.badge}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          <div className="flex-1 lg:overflow-y-auto px-5 py-5">
            {rightTab === 'steps' && (
              session ? (
                <StepsPanel steps={session.steps} currentStep={session.current_step} sessionCompleted={sessionCompleted ?? false}
                  solutionNo={session.solution_no} approach={session.approach} alternatives={session.alternatives}
                  onAlternative={(a) => altSession.mutate(a.title)} startingAlternative={altSession.isPending ? altSession.variables : null} />
              ) : (
                <EmptyState
                  icon={<Route size={24} />} tone="marker"
                  title={startSession.isPending ? t('task.preparingFirstStep') : t('task.startTitle')}
                  text={t('task.startPrompt')}
                  loading={startSession.isPending}
                  steps={[
                    { icon: <Play size={14} className="text-cobalt" />, title: t('how.s1'), text: t('how.s1t') },
                    { icon: <Lightbulb size={14} className="text-marker-deep" />, title: t('how.s2'), text: t('how.s2t') },
                    { icon: <FlaskConical size={14} className="text-ok" />, title: t('how.s3'), text: t('how.s3t') },
                  ]}
                  action={showSession && !restricted && !startSession.isPending && (
                    <button onClick={() => startSession.mutate()} className="btn-primary"><Play size={15} /> {t('task.startSession')}</button>
                  )}
                />
              )
            )}

            {rightTab === 'chat' && <AgentChat messages={messages} isLoading={agentLoading} />}

            {rightTab === 'preview' && info.web && <WebPreview code={code} />}

            {rightTab === 'tests' && (
              testsRunning || submitting ? (
                <EmptyState icon={<FlaskConical size={22} />} tone="ok" compact
                  title={queuePos != null && queuePos > 0 ? t('submit.queued', { n: queuePos }) : submitting ? t('submit.running') : t('task.testsRunning')}
                  text={queuePos != null ? t('submit.queuedHint') : ''} loading />
              ) : submitError ? (
                <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{submitError}</p>
              ) : testResults ? (
                <div className="space-y-4">
                  {submitResult && <SubmitSummary r={submitResult} />}
                  <TestsSummary key={testRunId} r={testResults} to={testsUrl}
                    onOpen={() => taskId && saveRun(taskId, { code, results: testResults, submit: submitResult, at: Date.now() })} />
                  {canImprove && testResults.passed === testResults.total && (
                    <button onClick={handleImprove} disabled={busy} className="btn-secondary w-full">
                      <Wand2 size={15} /> {t('improve.button')}
                      {policy?.mode === 'hints' && <span className="text-[11px] font-bold rounded-full bg-marker-soft text-marker-deep px-1.5 py-0.5 tabular-nums">{policy.improve_left}</span>}
                    </button>
                  )}
                  {!restricted && testResults.results.some((r) => r.error) && (
                    <div>
                      <button onClick={handleExplainErrors} disabled={explainLoading} className="btn-secondary w-full">
                        {explainLoading ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                        {explainLoading ? t('task.analyzingErrors') : t('task.explainErrors')}
                      </button>
                      {errorExplanation && (
                        <article className="mt-3 rounded-lg border border-line-soft border-l-[3px] border-l-marker bg-surface px-3.5 py-3">
                          <header className="flex items-center gap-1.5 text-[13px] font-bold text-marker-deep">
                            <Sparkles size={15} /> {t('task.explanationTitle')}
                          </header>
                          <div className="mt-1.5 note-md"><Markdown>{errorExplanation}</Markdown></div>
                        </article>
                      )}
                    </div>
                  )}
                </div>
              ) : submitResult ? (
                <SubmitSummary r={submitResult} />
              ) : errorExplanation ? (
                <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{errorExplanation}</p>
              ) : (
                <EmptyState
                  icon={<FlaskConical size={22} />} tone="ok" compact
                  title={t('task.testsEmptyTitle')}
                  text={session || restricted ? t('task.runPrompt') : t('task.startFirst')}
                  steps={[
                    { icon: <ListChecks size={14} className="text-cobalt" />, title: t('how.t1'), text: t('how.t1t') },
                    { icon: <ShieldAlert size={14} className="text-marker-deep" />, title: t('how.t2'), text: t('how.t2t') },
                  ]}
                />
              )
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}

/** Under the top bar when the task is opened from an assignment: deadline, points, Submit. */
function AssignmentBar({ a, points, best, submissions, onSubmit, submitting, examEnds, examNow }: {
  a: Assignment; points: number; best: number | null; submissions: number; onSubmit: () => void; submitting: boolean
  examEnds: number | null; examNow: number
}) {
  const { t } = useLanguage()
  const staff = a.my_role !== 'student'
  const exam = a.exam && !staff
  const can = staff || (exam ? a.exam_state === 'running' : a.status === 'open' || a.status === 'late')
  const left = examEnds ? countdown(new Date(examEnds).toISOString(), examNow) : null
  const urgent = examEnds != null && examEnds - examNow < 5 * 60_000
  return (
    <div className="bg-marker-soft border-b border-marker/40 px-3 sm:px-4 py-2 flex flex-wrap items-center gap-x-5 gap-y-1.5 shrink-0">
      <Link to={`/assignments/${a.id}`} className="inline-flex items-center gap-1.5 text-sm font-semibold hover:underline underline-offset-2 min-w-0">
        <ClipboardList size={15} className="shrink-0" /> <span className="truncate max-w-[16rem]">{a.title}</span>
      </Link>
      {exam ? (
        <span role="timer" className={`inline-flex items-center gap-1.5 text-[13px] font-semibold tabular-nums rounded-full px-2.5 py-0.5 ${
          urgent ? 'bg-bad text-white' : 'bg-surface text-ink border border-line'}`}>
          <Timer size={14} /> {a.exam_state === 'running' && left ? t('exam.timeLeft', { t: left }) : t('exam.over')}
        </span>
      ) : <Deadline a={a} live />}
      <span className="inline-flex items-center gap-1.5 text-[13px] text-ink-soft">
        {best != null || a.grades_published || !a.scores_after_publish ? <>{t('submit.best')} <Points got={best} max={points} /></>
          : <span className="text-ink-muted">{t('exam.pointsLater', { n: fmt(points) })}</span>}
        {submissions > 0 && <span className="text-ink-muted">· {(submissions === 1 ? t('assign.submissionOne') : t('assign.submissionsN', { n: submissions }))}</span>}
      </span>
      <div className="ml-auto flex items-center gap-2">
        {a.status === 'late' && <span className="text-[12px] font-semibold text-bad">{t('submit.latePenalty', { p: a.late_penalty })}</span>}
        <button onClick={onSubmit} disabled={!can || submitting} className="btn-primary btn-sm h-8"
          title={can ? t('submit.hint') : t('submit.closed')}>
          {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          {can ? t('submit.button') : t('submit.closedShort')}
        </button>
      </div>
    </div>
  )
}

/** In an assignment that limits the AI tutor: what is allowed right now and why. */
function PolicyBar({ policy }: { policy: AIPolicy }) {
  const { t } = useLanguage()
  return (
    <div className="bg-paper border-b border-line px-3 sm:px-4 py-1.5 flex items-center gap-2 text-[13px] text-ink-soft shrink-0">
      {policy.mode === 'off' ? <BotOff size={15} className="shrink-0" /> : <Lightbulb size={15} className="shrink-0 text-marker-deep" />}
      <span>
        {policy.mode === 'off' ? t('ai.offBar', { a: policy.assignment_title ?? '' })
          : t('ai.hintsBar', { a: policy.assignment_title ?? '', left: policy.hints_left ?? 0, limit: policy.hint_limit ?? 0 })}
      </span>
    </div>
  )
}

function SubmitSummary({ r }: { r: SubmitResult }) {
  const { t } = useLanguage()
  if (r.score == null) {
    return (
      <div className="rounded-lg px-3.5 py-3 border bg-surface border-line">
        <p className="text-[13px] font-semibold text-ink-soft flex items-center gap-1.5"><ShieldAlert size={14} /> {t('submit.done')}</p>
        <p className="mt-1 text-sm">
          {r.passed != null ? t('submit.testsPassed', { passed: r.passed, total: r.total ?? 0 }) : t('exam.resultsHidden')}
        </p>
        <p className="mt-0.5 text-[13px] text-ink-muted">{t('exam.pointsAfterPublish')}</p>
        {r.more_points && <MorePoints />}
      </div>
    )
  }
  const full = r.score >= r.max_points
  return (
    <div className={`rounded-lg px-3.5 py-3 border ${full ? 'bg-ok-soft border-ok/30' : 'bg-surface border-line'}`}>
      <p className="text-[13px] font-semibold text-ink-soft">{t('submit.done')}</p>
      <p className="mt-0.5 text-xl font-bold tabular-nums">
        <span className={full ? 'text-ok' : 'text-ink'}>{fmt(r.score)}</span>
        <span className="text-ink-muted text-base font-semibold"> / {fmt(r.max_points)} {t('assign.pointsShort')}</span>
      </p>
      <p className="mt-0.5 text-[13px] text-ink-muted">
        {r.passed != null ? t('submit.testsPassed', { passed: r.passed, total: r.total ?? 0 }) : t('exam.resultsHidden')}
        {r.late && <> · <span className="text-bad font-semibold">{t('submit.lateApplied', { p: r.late_penalty })}</span></>}
        {r.best_score != null && <>{' · '}{t('submit.bestNow', { n: fmt(r.best_score) })}</>}
      </p>
      {r.more_points && <MorePoints />}
    </div>
  )
}

/** Most tests pass but not all: the teacher may still give more points (never a promise). */
function MorePoints() {
  const { t } = useLanguage()
  return (
    <p className="mt-2.5 flex items-start gap-2 rounded-md bg-cobalt-soft px-3 py-2 text-[13px] text-ink">
      <TrendingUp size={15} className="shrink-0 mt-0.5 text-cobalt" />
      <span><span className="font-semibold">{t('morePoints.title')}</span> {t('morePoints.text')}</span>
    </p>
  )
}
