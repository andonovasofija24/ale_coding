import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import { adminApi } from '../../services/api'
import { TestCase } from '../../types'
import { ArrowLeft, Plus, Trash2, Save, Loader2 } from 'lucide-react'

interface TestCaseForm {
  id?: string
  type: 'code_sample' | 'stdin_stdout'
  test_code: string
  stdin: string
  expected_output: string
  is_hidden: boolean
  order: number
  _new?: boolean
}

export default function AdminTaskFormPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = !!taskId

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [starterCode, setStarterCode] = useState('')
  const [modelSolution, setModelSolution] = useState('')
  const [language, setLanguage] = useState('cpp')
  const [testCases, setTestCases] = useState<TestCaseForm[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const { data: task, isLoading } = useQuery({
    queryKey: ['admin-task', taskId],
    queryFn: () => adminApi.getTask(taskId!),
    enabled: isEdit,
  })

  useEffect(() => {
    if (task) {
      setTitle(task.title)
      setDescription(task.description)
      setStarterCode(task.starter_code)
      setModelSolution(task.model_solution)
      setLanguage(task.language)
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
      { type: 'code_sample', test_code: '', stdin: '', expected_output: '', is_hidden: false, order: prev.length, _new: true },
    ])
  }

  const removeTestCase = async (idx: number) => {
    const tc = testCases[idx]
    if (tc.id && isEdit) {
      await adminApi.deleteTestCase(taskId!, tc.id)
      qc.invalidateQueries({ queryKey: ['admin-task', taskId] })
    }
    setTestCases((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateTestCase = (idx: number, field: keyof TestCaseForm, value: string | boolean | number) => {
    setTestCases((prev) => prev.map((tc, i) => i === idx ? { ...tc, [field]: value } : tc))
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      if (isEdit) {
        await adminApi.updateTask(taskId!, { title, description, starter_code: starterCode, model_solution: modelSolution, language })
        // Add new test cases
        for (const tc of testCases.filter((t) => t._new)) {
          await adminApi.addTestCase(taskId!, {
            type: tc.type, test_code: tc.test_code, stdin: tc.stdin,
            expected_output: tc.expected_output, is_hidden: tc.is_hidden, order: tc.order,
          })
        }
        qc.invalidateQueries({ queryKey: ['admin-tasks'] })
        navigate('/admin/tasks')
      } else {
        await adminApi.createTask({
          title, description, starter_code: starterCode, model_solution: modelSolution, language,
          test_cases: testCases.map((tc) => ({
            type: tc.type, test_code: tc.test_code, stdin: tc.stdin,
            expected_output: tc.expected_output, is_hidden: tc.is_hidden, order: tc.order,
          })),
        })
        qc.invalidateQueries({ queryKey: ['admin-tasks'] })
        navigate('/admin/tasks')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (isEdit && isLoading) {
    return <div className="flex items-center justify-center h-screen"><Loader2 className="animate-spin" size={24} /></div>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <Link to="/admin/tasks" className="text-gray-500 hover:text-gray-700">
          <ArrowLeft size={18} />
        </Link>
        <h1 className="font-semibold text-gray-900">{isEdit ? 'Edit Task' : 'New Task'}</h1>
        <div className="ml-auto flex items-center gap-2">
          {error && <span className="text-red-600 text-sm">{error}</span>}
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save
          </button>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Basic info */}
        <div className="card p-5 space-y-4">
          <h2 className="font-semibold text-gray-800">Task Details</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Stack Implementation"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="cpp">C++ (cpp)</option>
                <option value="c">C</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (Markdown)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={8}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Task description in Markdown..."
            />
          </div>
        </div>

        {/* Starter code */}
        <div className="card p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Starter Code</h2>
          <div className="border border-gray-200 rounded-lg overflow-hidden" style={{ height: 200 }}>
            <Editor
              language="cpp"
              value={starterCode}
              onChange={(v) => setStarterCode(v || '')}
              options={{ fontSize: 12, minimap: { enabled: false }, scrollBeyondLastLine: false }}
              theme="vs-light"
            />
          </div>
        </div>

        {/* Model solution */}
        <div className="card p-5">
          <h2 className="font-semibold text-gray-800 mb-1">Model Solution</h2>
          <p className="text-xs text-gray-500 mb-3">Only visible to admins and the AI agent. Never shown to students.</p>
          <div className="border border-gray-200 rounded-lg overflow-hidden" style={{ height: 300 }}>
            <Editor
              language="cpp"
              value={modelSolution}
              onChange={(v) => setModelSolution(v || '')}
              options={{ fontSize: 12, minimap: { enabled: false }, scrollBeyondLastLine: false }}
              theme="vs-light"
            />
          </div>
        </div>

        {/* Test cases */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold text-gray-800">Test Cases</h2>
              <p className="text-xs text-gray-500">Hidden tests are run but not shown to students.</p>
            </div>
            <button onClick={addTestCase} className="btn-secondary text-sm py-1.5 px-3">
              <Plus size={13} /> Add Test
            </button>
          </div>

          {testCases.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">No test cases yet.</p>
          ) : (
            <div className="space-y-4">
              {testCases.map((tc, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-gray-700">Test {idx + 1}</span>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-1.5 text-xs text-gray-600">
                        <input
                          type="checkbox"
                          checked={tc.is_hidden}
                          onChange={(e) => updateTestCase(idx, 'is_hidden', e.target.checked)}
                        />
                        Hidden
                      </label>
                      <button onClick={() => removeTestCase(idx)} className="text-red-500 hover:text-red-700">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                      <select
                        value={tc.type}
                        onChange={(e) => updateTestCase(idx, 'type', e.target.value)}
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs"
                      >
                        <option value="code_sample">Code sample (snippet in main)</option>
                        <option value="stdin_stdout">Stdin / Stdout</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Order</label>
                      <input
                        type="number"
                        value={tc.order}
                        onChange={(e) => updateTestCase(idx, 'order', parseInt(e.target.value))}
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs"
                      />
                    </div>
                  </div>

                  {tc.type === 'code_sample' ? (
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Test snippet (goes inside main)</label>
                      <textarea
                        value={tc.test_code}
                        onChange={(e) => updateTestCase(idx, 'test_code', e.target.value)}
                        rows={3}
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs font-mono"
                        placeholder={'ExamResult e("001", "Stefan", 60, 80);\ncout << e.finalPoints() << endl;'}
                      />
                    </div>
                  ) : (
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Stdin</label>
                      <textarea
                        value={tc.stdin}
                        onChange={(e) => updateTestCase(idx, 'stdin', e.target.value)}
                        rows={2}
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs font-mono"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Expected output</label>
                    <textarea
                      value={tc.expected_output}
                      onChange={(e) => updateTestCase(idx, 'expected_output', e.target.value)}
                      rows={2}
                      className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs font-mono"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
