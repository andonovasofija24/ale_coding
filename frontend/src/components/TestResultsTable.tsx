import { useState } from 'react'
import { TestResult } from '../types'
import { CheckCircle2, XCircle, ChevronDown, Lock } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import ResultTable from './ResultTable'

interface Props {
  results: TestResult[]
  passed: number
  total: number
  /** SQL: show expected / actual results as tables. */
  tables?: boolean
}

/** Test run summary + one expandable row per test. Failed tests open by default. */
export default function TestResultsTable({ results, passed, total, tables = false }: Props) {
  const { t } = useLanguage()
  const [open, setOpen] = useState<Set<number>>(
    () => new Set(results.filter((r) => !r.passed).map((r) => r.test_number))
  )
  const allPassed = passed === total

  const toggle = (n: number) =>
    setOpen((prev) => {
      const next = new Set(prev)
      next.has(n) ? next.delete(n) : next.add(n)
      return next
    })

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h3 className="panel-title">{t('results.title')}</h3>
        <span className={`text-sm font-bold tabular-nums ${allPassed ? 'text-ok' : 'text-bad'}`}>
          {t('results.passed', { passed, total })}
        </span>
      </div>
      <div className="mt-2 flex gap-1" aria-hidden>
        {results.map((r) => (
          <span key={r.test_number} className={`h-1.5 flex-1 rounded-full ${r.passed ? 'bg-ok' : 'bg-bad'}`} />
        ))}
      </div>

      <ul className="mt-4 space-y-2">
        {results.map((r) => {
          const isOpen = open.has(r.test_number)
          return (
            <li key={r.test_number} className="rounded-lg border border-line-soft bg-surface overflow-hidden">
              <button
                onClick={() => toggle(r.test_number)}
                aria-expanded={isOpen}
                className="w-full flex items-center gap-2 px-3 py-2.5 text-sm hover:bg-paper/60 transition-colors"
              >
                {r.passed ? <CheckCircle2 size={16} className="text-ok" /> : <XCircle size={16} className="text-bad" />}
                <span className="font-semibold">{t('task.test')} {r.test_number}</span>
                {r.hidden && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-ink-muted bg-paper rounded-full px-1.5 py-0.5">
                    <Lock size={11} /> {t('results.hidden')}
                  </span>
                )}
                <span className={`text-xs ${r.passed ? 'text-ok' : 'text-bad'}`}>
                  {r.passed ? t('results.ok') : r.error ? t('results.errored') : r.type === 'diagram' ? t('dg.notMet') : t('results.wrong')}
                </span>
                <ChevronDown size={15} className={`ml-auto text-ink-faint transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>

              {isOpen && r.hidden && !r.expected_output && (
                <p className="px-3 pb-3 text-xs text-ink-muted leading-relaxed">
                  {r.passed ? t('results.hiddenPassed') : t('results.hiddenFailed', { kind: errorKind(r.error, t) })}
                </p>
              )}
              {isOpen && !(r.hidden && !r.expected_output) && (
                <div className="px-3 pb-3 space-y-2.5 text-xs">
                  {r.test_code && r.type !== 'diagram' && (
                    <div>
                      <p className="text-ink-muted mb-1">{tables ? t('task.testData') : t('results.colTest')}</p>
                      <pre className={`code-block ${tables ? 'max-h-32 overflow-auto' : ''}`}>{r.test_code}</pre>
                    </div>
                  )}
                  {r.stdin && (
                    <div>
                      <p className="text-ink-muted mb-1">{t('results.colInput')}</p>
                      <pre className="code-block">{r.stdin}</pre>
                    </div>
                  )}
                  {tables ? (
                    <div className="space-y-2">
                      <div>
                        <p className="text-ink-muted mb-1">{t('results.colExpected')}</p>
                        <ResultTable text={r.expected_output} tone="ok" />
                      </div>
                      <div>
                        <p className="text-ink-muted mb-1">{t('results.colGot')}</p>
                        {r.error ? <p className="text-ink-muted">—</p>
                          : <ResultTable text={r.actual_output} tone={r.passed ? 'ok' : 'bad'} emptyLabel={t('results.nothing')} />}
                      </div>
                    </div>
                  ) : (
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-ink-muted mb-1">{r.type === 'diagram' ? t('dg.check') : t('results.colExpected')}</p>
                      <pre className={`code-block text-ok min-h-[2.25rem] ${r.type === 'diagram' ? 'font-sans whitespace-pre-wrap' : ''}`}>{r.expected_output}</pre>
                    </div>
                    <div>
                      <p className="text-ink-muted mb-1">{r.type === 'diagram' ? t('dg.found') : t('results.colGot')}</p>
                      <pre className={`code-block min-h-[2.25rem] ${r.type === 'diagram' ? 'font-sans whitespace-pre-wrap' : ''} ${r.passed ? 'text-ok' : 'text-bad'}`}>
                        {r.error ? '—' : r.actual_output || t('results.nothing')}
                      </pre>
                    </div>
                  </div>
                  )}
                  {r.images && (
                    <div>
                      <p className="text-ink-muted mb-1">{t('web.visualCompare', { size: r.images.viewport ?? '' })}</p>
                      <div className="grid grid-cols-2 gap-2">
                        {(['actual', 'expected'] as const).map((k) => (
                          <figure key={k} className="rounded-lg border border-line-soft overflow-hidden bg-paper">
                            <img src={r.images![k]} alt={k === 'actual' ? t('web.yourPage') : t('web.modelPage')} className="w-full block" />
                            <figcaption className="px-2 py-1 text-[11px] font-semibold text-ink-soft">{k === 'actual' ? t('web.yourPage') : t('web.modelPage')}</figcaption>
                          </figure>
                        ))}
                      </div>
                    </div>
                  )}
                  {r.error && (
                    <pre className="font-mono text-[11.5px] leading-relaxed rounded-lg bg-bad-soft text-bad px-3 py-2 whitespace-pre-wrap max-h-48 overflow-auto">
                      {r.error}
                    </pre>
                  )}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/** Readable name of the failure kind ("COMPILE ERROR" -> "compile error", no error -> "wrong output"). */
function errorKind(error: string | undefined, t: (k: any) => string): string {
  if (!error) return t('results.kind.wrong')
  if (error.startsWith('COMPILE')) return t('results.kind.compile')
  if (error.startsWith('TIME LIMIT')) return t('results.kind.time')
  return t('results.kind.runtime')
}
