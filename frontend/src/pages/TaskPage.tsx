import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import ReactMarkdown from 'react-markdown'
import { tasksApi, sessionsApi } from '../services/api'
import { Task, Session, AgentMessage, RunTestsResponse } from '../types'
import StepsPanel from '../components/StepsPanel'
import AgentChat from '../components/AgentChat'
import TestResultsTable from '../components/TestResultsTable'
import {
  ArrowLeft, Play, CheckSquare, Lightbulb, ChevronRight,
  FlaskConical, Loader2, BookOpen, MessageSquare, RotateCcw, Sparkles
} from 'lucide-react'

type RightTab = 'steps' | 'chat' | 'tests'

export default function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const qc = useQueryClient()

  const [code, setCode] = useState<string>('')
  const [codeInitialized, setCodeInitialized] = useState(false)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [agentLoading, setAgentLoading] = useState(false)
  const [testResults, setTestResults] = useState<RunTestsResponse | null>(null)
  const [errorExplanation, setErrorExplanation] = useState<string | null>(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [rightTab, setRightTab] = useState<RightTab>('steps')
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: task } = useQuery<Task>({
    queryKey: ['task', taskId],
    queryFn: () => tasksApi.get(taskId!),
  })

  const { data: session, isLoading: sessionLoading } = useQuery<Session | null>({
    queryKey: ['session', taskId],
    queryFn: () => sessionsApi.getForTask(taskId!),
    enabled: !!taskId,
  })

  useEffect(() => {
    if (!codeInitialized && (session !== undefined || task)) {
      setCode(session?.current_code || task?.starter_code || '')
      setCodeInitialized(true)
    }
  }, [session, task, codeInitialized])

  const startSession = useMutation({
    mutationFn: () => sessionsApi.start(taskId!),
    onSuccess: (newSession: Session) => {
      qc.setQueryData(['session', taskId], newSession)
      setCode(newSession.current_code || task?.starter_code || '')
      setCodeInitialized(true)
    },
  })

  const newSession = useMutation({
    mutationFn: () => sessionsApi.startNew(taskId!),
    onSuccess: (fresh: Session) => {
      qc.setQueryData(['session', taskId], fresh)
      setCode(fresh.current_code || task?.starter_code || '')
      setCodeInitialized(true)
      setTestResults(null)
      setErrorExplanation(null)
      setMessages([])
      setRightTab('steps')
    },
  })

  const handleCodeChange = useCallback((val: string | undefined) => {
    const v = val ?? ''
    setCode(v)
    if (session) {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        sessionsApi.saveCode(session.id, v).catch(() => {})
      }, 2000)
    }
  }, [session])

  const handleCheckStep = async () => {
    if (!session) return
    setAgentLoading(true)
    setRightTab('chat')
    setMessages((m) => [...m, { role: 'user', content: `Checking step ${session.current_step + 1}...`, timestamp: new Date() }])
    try {
      const result = await sessionsApi.checkStep(session.id, code)
      setMessages((m) => [...m, { role: 'assistant', content: result.feedback, timestamp: new Date() }])
      if (result.passed) {
        qc.invalidateQueries({ queryKey: ['session', taskId] })
        setRightTab('steps')
      }
    } catch (err: any) {
      setMessages((m) => [...m, { role: 'assistant', content: err.response?.data?.detail || 'Error checking step.', timestamp: new Date() }])
    } finally {
      setAgentLoading(false)
    }
  }

  const handleHint = async () => {
    if (!session) return
    setAgentLoading(true)
    setRightTab('chat')
    setMessages((m) => [...m, { role: 'user', content: 'Give me a hint for the current step.', timestamp: new Date() }])
    try {
      const result = await sessionsApi.getHint(session.id, code)
      setMessages((m) => [...m, { role: 'assistant', content: result.hint, timestamp: new Date() }])
    } catch (err: any) {
      setMessages((m) => [...m, { role: 'assistant', content: 'Could not get hint right now.', timestamp: new Date() }])
    } finally {
      setAgentLoading(false)
    }
  }

  const handleRunTests = async () => {
    if (!taskId) return
    setAgentLoading(true)
    setRightTab('tests')
    setErrorExplanation(null)
    try {
      const results = await sessionsApi.runTests(taskId, code)
      setTestResults(results)
    } catch (err: any) {
      console.error('Run tests error', err)
    } finally {
      setAgentLoading(false)
    }
  }

  const handleExplainErrors = async () => {
    if (!taskId || !testResults) return
    const errors = testResults.results
      .filter((r) => r.error)
      .map((r) => r.error as string)
    if (errors.length === 0) return
    setExplainLoading(true)
    try {
      const res = await sessionsApi.explainErrors(taskId, code, errors)
      setErrorExplanation(res.explanation)
    } catch (err: any) {
      console.error('Explain errors failed', err)
    } finally {
      setExplainLoading(false)
    }
  }

  const activeStep = session?.steps.find((s) => s.step_number === session.current_step)
  const stepCompleted = activeStep?.status === 'completed'
  const sessionCompleted = session?.status === 'completed'
  const canProceed = stepCompleted || sessionCompleted

  if (!task) {
    return (
      <div className="flex items-center justify-center h-screen text-gray-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading task...
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gray-100 overflow-hidden">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-2.5 flex items-center gap-3 shrink-0">
        <Link to="/tasks" className="text-gray-500 hover:text-gray-700">
          <ArrowLeft size={18} />
        </Link>
        <h1 className="font-semibold text-gray-900 truncate">{task.title}</h1>
        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium uppercase ml-1">
          {task.language}
        </span>
        <div className="ml-auto flex items-center gap-2">
          {sessionCompleted && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
              Completed
            </span>
          )}
          {session && (
            <button
              onClick={() => {
                if (confirm('Start a new session? Your current progress will be reset.')) {
                  newSession.mutate()
                }
              }}
              disabled={newSession.isPending}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded px-2 py-1 transition-colors"
              title="Start a new session from scratch"
            >
              {newSession.isPending ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
              New Session
            </button>
          )}
        </div>
      </header>

      {/* Main layout: description | editor | right panel */}
      <div className="flex flex-1 overflow-hidden gap-px bg-gray-200">
        {/* Left: Task description */}
        <div className="w-72 shrink-0 bg-white flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
              <BookOpen size={14} />
              Task Description
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-3 task-description text-sm">
            <ReactMarkdown>{task.description}</ReactMarkdown>
          </div>

          {/* Visible test cases */}
          {task.test_cases.length > 0 && (
            <div className="border-t border-gray-100 px-4 py-3">
              <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Example Tests</p>
              <div className="space-y-2">
                {task.test_cases.map((tc, i) => (
                  <div key={tc.id} className="bg-gray-50 rounded-lg p-2 text-xs">
                    <div className="text-gray-500 mb-1">Test {i + 1}</div>
                    {tc.test_code && (
                      <pre className="font-mono text-gray-700 whitespace-pre-wrap mb-1">{tc.test_code}</pre>
                    )}
                    {tc.stdin && (
                      <div><span className="text-gray-400">In:</span> <pre className="inline font-mono">{tc.stdin}</pre></div>
                    )}
                    <div><span className="text-gray-400">Out:</span> <pre className="inline font-mono text-green-700">{tc.expected_output}</pre></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Center: Code editor */}
        <div className="flex-1 bg-white flex flex-col overflow-hidden">
          <div className="px-4 py-2.5 border-b border-gray-100 flex items-center justify-between shrink-0">
            <span className="text-sm font-medium text-gray-600">solution.cpp</span>
            <div className="flex items-center gap-1 text-xs text-gray-400">
              Auto-saved
            </div>
          </div>

          <div className="flex-1">
            <Editor
              language={task.language === 'cpp' ? 'cpp' : task.language}
              value={code}
              onChange={handleCodeChange}
              options={{
                fontSize: 13,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                tabSize: 4,
                automaticLayout: true,
                padding: { top: 12 },
              }}
              theme="vs-light"
            />
          </div>

          {/* Action bar */}
          <div className="border-t border-gray-100 px-4 py-2.5 flex items-center gap-2 shrink-0 bg-white">
            {!session && !sessionLoading && (
              <button
                onClick={() => startSession.mutate()}
                disabled={startSession.isPending}
                className="btn-primary"
              >
                {startSession.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                Start Session
              </button>
            )}
            {session && !sessionCompleted && (
              <>
                <button onClick={handleCheckStep} disabled={agentLoading} className="btn-primary">
                  {agentLoading ? <Loader2 size={14} className="animate-spin" /> : <CheckSquare size={14} />}
                  Check Step
                </button>
                <button onClick={handleHint} disabled={agentLoading} className="btn-secondary">
                  <Lightbulb size={14} />
                  Hint
                </button>
              </>
            )}
            <button
              onClick={handleRunTests}
              disabled={agentLoading || !session}
              className="btn-secondary ml-auto"
            >
              {agentLoading && rightTab === 'tests' ? <Loader2 size={14} className="animate-spin" /> : <FlaskConical size={14} />}
              Run All Tests
            </button>
          </div>
        </div>

        {/* Right: Steps / Chat / Tests */}
        <div className="w-80 shrink-0 bg-white flex flex-col overflow-hidden">
          {/* Tab bar */}
          <div className="flex border-b border-gray-100 shrink-0">
            {([
              { key: 'steps', icon: <ChevronRight size={13} />, label: 'Steps' },
              { key: 'chat', icon: <MessageSquare size={13} />, label: 'Feedback' },
              { key: 'tests', icon: <FlaskConical size={13} />, label: 'Tests' },
            ] as const).map((tab) => (
              <button
                key={tab.key}
                onClick={() => setRightTab(tab.key)}
                className={`flex-1 flex items-center justify-center gap-1 py-2.5 text-xs font-medium transition-colors ${
                  rightTab === tab.key
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden">
            {rightTab === 'steps' && session && (
              <div className="overflow-y-auto h-full p-3">
                <StepsPanel
                  steps={session.steps}
                  currentStep={session.current_step}
                  sessionCompleted={sessionCompleted ?? false}
                />
              </div>
            )}
            {rightTab === 'steps' && !session && (
              <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm gap-2 text-center p-3">
                <ChevronRight size={28} className="opacity-30" />
                <p>Click "Start Session" to begin the guided learning flow.</p>
              </div>
            )}
            {rightTab === 'chat' && (
              <div className="h-full p-3">
                <AgentChat messages={messages} isLoading={agentLoading && rightTab === 'chat'} />
              </div>
            )}
            {rightTab === 'tests' && (
              <div className="overflow-y-auto h-full p-3 space-y-3">
                {testResults ? (
                  <>
                    <TestResultsTable
                      results={testResults.results}
                      passed={testResults.passed}
                      total={testResults.total}
                    />
                    {testResults.results.some((r) => r.error) && (
                      <div>
                        <button
                          onClick={handleExplainErrors}
                          disabled={explainLoading}
                          className="flex items-center gap-1.5 text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded px-3 py-1.5 transition-colors w-full justify-center"
                        >
                          {explainLoading
                            ? <Loader2 size={13} className="animate-spin" />
                            : <Sparkles size={13} />}
                          {explainLoading ? 'Analyzing errors...' : 'Explain errors with AI'}
                        </button>
                        {errorExplanation && (
                          <div className="mt-2 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 leading-relaxed whitespace-pre-wrap">
                            {errorExplanation}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm gap-2">
                    <FlaskConical size={28} className="opacity-30" />
                    <p>Click "Run All Tests" to see results.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
