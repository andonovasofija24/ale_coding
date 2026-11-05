import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Eye, Loader2, X, AlertTriangle, RotateCcw, HelpCircle, Lightbulb, Crosshair } from 'lucide-react'
import { tasksApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { TestCase, TestVisualization, VizStructure } from '../types'
import ResultTable from './ResultTable'

interface Props {
  taskId: string
  testCase: TestCase
  testNumber: number
  onClose: () => void
  /** SQL: outputs are result tables. */
  tables?: boolean
}

/** Modal that steps through an AI-generated trace of one visible example test. */
export default function TestVisualizer({ taskId, testCase, testNumber, onClose, tables = false }: Props) {
  const { t, lang, tError } = useLanguage()
  const [idx, setIdx] = useState(0)

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery<TestVisualization>({
    queryKey: ['viz', taskId, testCase.id, lang],
    queryFn: () => tasksApi.visualize(taskId, testCase.id),
    staleTime: Infinity,
    retry: 0,
  })

  const frames = data?.frames ?? []
  const at = Math.min(idx, Math.max(frames.length - 1, 0))
  const frame = frames[at]
  const prev = at > 0 ? frames[at - 1] : undefined

  useEffect(() => setIdx(0), [data])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') setIdx((i) => Math.min(i + 1, frames.length - 1))
      if (e.key === 'ArrowLeft') setIdx((i) => Math.max(i - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [frames.length, onClose])

  const isStdin = testCase.type === 'stdin_stdout'
  const sourceLines = (isStdin ? testCase.stdin : testCase.test_code).replace(/\n$/, '').split('\n')

  return (
    <div className="fixed inset-0 z-50 bg-ink/50 backdrop-blur-[2px] flex items-center justify-center p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className="bg-surface rounded-2xl shadow-modal w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-line-soft">
          <Eye size={16} className="text-cobalt" />
          <h2 className="font-semibold text-ink">{t('viz.title', { n: testNumber })}</h2>
          <button onClick={onClose} className="ml-auto text-ink-faint hover:text-ink-soft" aria-label={t('viz.close')}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        {isLoading || (isFetching && !data) ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20 text-ink-muted text-sm">
            <Loader2 className="animate-spin text-cobalt" size={24} />
            {t('viz.loading')}
          </div>
        ) : isError || !frame ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20 text-sm">
            <AlertTriangle className="text-marker-deep" size={24} />
            <p className="text-ink-soft">{tError((error as any)?.response?.data?.detail, 'viz.error')}</p>
            <button onClick={() => refetch()} className="btn-secondary text-sm py-1.5 px-3">
              <RotateCcw size={13} /> {t('viz.retry')}
            </button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto grid md:grid-cols-2 gap-px bg-line-soft">
            {/* Left: test source with current line */}
            <div className="bg-surface p-5 space-y-4">
              <div>
                <p className="panel-title mb-2">
                  {isStdin ? t('viz.input') : tables ? t('viz.testData') : t('viz.testCode')}
                </p>
                <div className="rounded-lg bg-ink text-white/90 font-mono text-xs py-2 overflow-x-auto">
                  {sourceLines.map((ln, i) => {
                    const active = frame.line === i + 1
                    return (
                      <div
                        key={i}
                        className={`flex gap-3 px-3 py-0.5 ${active ? 'bg-marker text-ink font-medium' : ''}`}
                      >
                        <span className={`select-none w-4 text-right ${active ? 'text-ink' : 'text-white/35'}`}>
                          {active ? '▶' : i + 1}
                        </span>
                        <span className="whitespace-pre">{ln || ' '}</span>
                      </div>
                    )
                  })}
                </div>
                {frame.line === 0 && frame.code && (
                  <p className="mt-2 text-xs text-ink-muted font-mono">▶ {frame.code}</p>
                )}
              </div>

              <div>
                <p className="panel-title mb-2">{t('viz.expected')}</p>
                {tables ? <ResultTable text={testCase.expected_output} tone="ok" /> : (
                  <pre className="rounded-lg bg-paper/70 border border-line-soft px-3 py-2 font-mono text-xs text-ok whitespace-pre-wrap">
                    {testCase.expected_output}
                  </pre>
                )}
              </div>
            </div>

            {/* Right: state after this frame */}
            <div className="bg-surface p-5 space-y-4">
              <div className="rounded-lg bg-marker-soft border border-marker/50 px-3.5 py-2.5 text-[14.5px] text-ink leading-relaxed">
                {frame.explanation}
              </div>
              {frame.why && (
                <div className="rounded-lg border-l-4 border-cobalt bg-cobalt-soft/60 px-3 py-2">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-cobalt flex items-center gap-1"><HelpCircle size={12} /> {t('viz.why')}</p>
                  <p className="mt-0.5 text-[13.5px] leading-relaxed text-ink">{frame.why}</p>
                </div>
              )}
              {frame.tip && (
                <div className="rounded-lg border-l-4 border-marker bg-paper px-3 py-2">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-marker-deep flex items-center gap-1"><Lightbulb size={12} /> {t('viz.tip')}</p>
                  <p className="mt-0.5 text-[13px] leading-relaxed text-ink-soft">{frame.tip}</p>
                </div>
              )}

              {frame.exception && (
                <div className="rounded-lg bg-bad-soft px-3 py-2 text-xs text-bad flex gap-2">
                  <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                  <span><b>{t('viz.exception')}</b> {frame.exception}</span>
                </div>
              )}

              {frame.structures.length > 0 && (
                <div>
                  <p className="panel-title mb-2">{t('viz.state')}</p>
                  <div className="flex flex-wrap gap-4 items-start">
                    {frame.structures.map((st, i) => (
                      <Structure key={`${st.name}-${i}`} s={st} before={prev?.structures.find((p) => p.name === st.name && p.kind === st.kind)}
                        focus={!!frame.focus && frame.focus === st.name} focusIndex={frame.focus_index ?? -1} focusField={frame.focus_field ?? ''} />
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="panel-title mb-2">{tables ? t('viz.result') : t('viz.output')}</p>
                {tables ? (
                  frame.output ? <ResultTable text={frame.output} /> : <p className="text-xs text-ink-muted">{t('viz.noResultYet')}</p>
                ) : (
                  <pre className="rounded-lg bg-ink text-[#9BE3BF] font-mono text-xs px-3 py-2 min-h-[2.5rem] whitespace-pre-wrap">
                    {frame.output || <span className="text-ink-muted">{t('viz.noOutput')}</span>}
                  </pre>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer: stepper */}
        {frames.length > 0 && !isError && (
          <div className="flex items-center gap-3 px-5 py-3 border-t border-line-soft">
            <button
              onClick={() => setIdx((i) => Math.max(i - 1, 0))}
              disabled={idx === 0}
              className="btn-secondary text-sm py-1.5 px-3"
            >
              <ChevronLeft size={14} /> {t('viz.prev')}
            </button>
            <div className="flex-1 flex flex-col items-center gap-1.5">
              <span className="text-xs text-ink-muted">{t('viz.stepOf', { n: idx + 1, total: frames.length })}</span>
              {frames.length > 30 ? (
                <input type="range" min={0} max={frames.length - 1} value={at} onChange={(e) => setIdx(Number(e.target.value))}
                  className="w-full max-w-xs accent-ink" aria-label={t('viz.stepOf', { n: at + 1, total: frames.length })} />
              ) : (
              <div className="flex gap-1 flex-wrap justify-center">
                {frames.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setIdx(i)}
                    aria-label={t('viz.stepOf', { n: i + 1, total: frames.length })}
                    className={`h-1.5 rounded-full transition-all ${i === idx ? 'w-5 bg-ink' : 'w-1.5 bg-line hover:bg-ink-faint'}`}
                  />
                ))}
              </div>
              )}
            </div>
            <button
              onClick={() => setIdx((i) => Math.min(i + 1, frames.length - 1))}
              disabled={idx >= frames.length - 1}
              className="btn-primary text-sm py-1.5 px-3"
            >
              {t('viz.next')} <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function cellClass(highlighted: boolean, focused = false) {
  return focused
    ? 'border-cobalt bg-cobalt-soft text-ink font-bold ring-2 ring-cobalt/40 z-10'
    : highlighted
      ? 'border-ink bg-marker text-ink font-bold'
      : 'border-line bg-surface text-ink'
}

/** One structure. `focus`: it is what is being processed right now (ringed, "now" badge; the item `focusIndex` /
 *  field `focusField` in it is marked). `before`: the same structure in the previous moment (to show what was). */
function Structure(props: { s: VizStructure; before?: VizStructure; focus?: boolean; focusIndex?: number; focusField?: string }) {
  const body = <StructureBody {...props} />
  if (!props.focus) return body
  return (
    <div className="relative rounded-lg border-2 border-cobalt bg-cobalt-soft/30 px-2 pb-1.5 pt-3.5 -mx-2 -mb-1.5">
      <span className="absolute -top-2.5 left-2 inline-flex items-center gap-1 rounded-full bg-cobalt text-white text-[10px] font-bold px-1.5 py-0.5 animate-pulse">
        <Crosshair size={10} /> <NowLabel />
      </span>
      {body}
    </div>
  )
}

function NowLabel() {
  const { t } = useLanguage()
  return <>{t('viz.now')}</>
}

function StructureBody({ s, before, focus = false, focusIndex = -1, focusField = '' }: { s: VizStructure; before?: VizStructure; focus?: boolean; focusIndex?: number; focusField?: string }) {
  const { t } = useLanguage()
  const fi = focus ? focusIndex : -1
  const label = (
    <div className="text-xs text-ink-muted mb-1 font-mono">
      {s.type ? <span className="text-obj">{s.type} </span> : null}
      {s.name}
    </div>
  )
  const was = (now: string, old?: string) => old !== undefined && old !== now
    ? <span className="block text-[10px] text-ink-faint font-mono line-through" title={t('viz.was')}>{old}</span> : null

  if (s.kind === 'stack') {
    // items are bottom -> top; draw top first
    const order = s.items.map((v, i) => ({ v, i })).reverse()
    return (
      <div>
        {label}
        <div className="flex flex-col items-start">
          {order.length === 0 && (
            <div className="w-20 h-9 border-2 border-dashed border-line rounded flex items-center justify-center text-[11px] text-ink-faint">
              {t('viz.empty')}
            </div>
          )}
          {order.map(({ v, i }, k) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-20 h-9 border-2 -mt-px flex items-center justify-center font-mono text-sm ${cellClass(s.highlight.includes(i), i === fi)} ${k === 0 ? 'rounded-t' : ''} ${k === order.length - 1 ? 'rounded-b' : ''}`}>
                {v}
              </div>
              {k === 0 && <span className="text-[11px] text-ink-muted">← {t('viz.top')}</span>}
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (s.kind === 'array' || s.kind === 'queue') {
    return (
      <div>
        {label}
        {s.items.length === 0 ? (
          <div className="h-9 px-3 border-2 border-dashed border-line rounded flex items-center text-[11px] text-ink-faint">
            {t('viz.empty')}
          </div>
        ) : (
          <div className="flex">
            {s.items.map((v, i) => (
              <div key={i} className="flex flex-col items-center">
                <div className={`min-w-[2.25rem] h-9 px-2 border-2 -ml-px flex items-center justify-center font-mono text-sm ${cellClass(s.highlight.includes(i), i === fi)} ${i === 0 ? 'rounded-l' : ''} ${i === s.items.length - 1 ? 'rounded-r' : ''}`}>
                  {v}
                </div>
                <span className={`text-[10px] mt-0.5 ${i === fi ? 'text-cobalt font-bold' : 'text-ink-faint'}`}>
                  {i === fi ? '▲' : s.kind === 'queue' ? (i === 0 ? t('viz.front') : i === s.items.length - 1 ? t('viz.back') : '') : i}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (s.kind === 'table') {
    const text = [s.columns.join(' | '), ...s.rows.map((r) => r.join(' | '))].join('\n')
    return (
      <div className="min-w-0 max-w-full">
        {label}
        <ResultTable text={text} highlight={fi >= 0 ? [...s.highlight, fi] : s.highlight} emptyLabel={t('viz.emptyTable')} />
      </div>
    )
  }

  if (s.kind === 'object') {
    return (
      <div className="rounded-lg border-2 border-obj/30 bg-obj-soft min-w-[8rem]">
        <div className="px-3 py-1 border-b border-obj/30 text-xs font-mono">
          <span className="text-obj">{s.type || 'object'}</span> {s.name}
        </div>
        <table className="text-xs font-mono">
          <tbody>
            {s.fields.map((f, i) => {
              const on = focus && focusField === f.name
              return (
                <tr key={i} className={on ? 'bg-cobalt-soft' : ''}>
                  <td className={`px-3 py-0.5 ${on ? 'text-cobalt font-bold' : 'text-ink-muted'}`}>{on ? '▶ ' : ''}{f.name}</td>
                  <td className="px-3 py-0.5 text-ink">{f.value}{was(f.value, before?.fields.find((x) => x.name === f.name)?.value)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  // value
  return (
    <div>
      {label}
      <div className={`min-h-9 px-3 py-1 border-2 rounded flex flex-col justify-center font-mono text-sm text-ink ${
        focus ? 'border-cobalt bg-cobalt-soft font-bold' : before && before.value !== s.value ? 'border-ink bg-marker' : 'border-line bg-surface'}`}>
        {s.value}
        {was(s.value, before?.value)}
      </div>
    </div>
  )
}
