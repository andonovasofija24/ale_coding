import { TestResult } from '../types'
import { CheckCircle2, XCircle } from 'lucide-react'

interface Props {
  results: TestResult[]
  passed: number
  total: number
}

export default function TestResultsTable({ results, passed, total }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm text-gray-700">Test Results</h3>
        <span className={`text-sm font-medium ${passed === total ? 'text-green-600' : 'text-red-600'}`}>
          {passed}/{total} passed
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-3 py-2 text-left font-medium text-gray-500 w-8">#</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Test</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Input</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Expected</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Got</th>
              <th className="px-3 py-2 text-center font-medium text-gray-500 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.test_number} className={`border-b border-gray-100 ${r.passed ? 'bg-green-50/50' : 'bg-red-50/50'}`}>
                <td className="px-3 py-2 text-gray-400">{r.test_number}</td>
                <td className="px-3 py-2">
                  <pre className="whitespace-pre-wrap font-mono text-gray-700 max-w-[200px]">{r.test_code || '—'}</pre>
                </td>
                <td className="px-3 py-2">
                  <pre className="whitespace-pre-wrap font-mono text-gray-700">{r.stdin || '—'}</pre>
                </td>
                <td className="px-3 py-2">
                  <pre className="whitespace-pre-wrap font-mono text-gray-700">{r.expected_output}</pre>
                </td>
                <td className="px-3 py-2">
                  {r.error ? (
                    <pre className="whitespace-pre-wrap font-mono text-red-700 text-[10px]">{r.error}</pre>
                  ) : (
                    <pre className="whitespace-pre-wrap font-mono text-gray-700">{r.actual_output}</pre>
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  {r.passed ? (
                    <CheckCircle2 size={14} className="text-green-500 mx-auto" />
                  ) : (
                    <XCircle size={14} className="text-red-500 mx-auto" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
