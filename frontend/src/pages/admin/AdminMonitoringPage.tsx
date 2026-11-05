import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { RefreshCw, AlertTriangle, CheckCircle2, Cpu, ShieldCheck } from 'lucide-react'
import { adminApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { LOCALES } from '../../i18n/translations'
import { MonitoringData } from '../../types'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import LangChip from '../../components/LangChip'

type Range = '24h' | '7d' | '30d'

// Series colours (validated: CVD-safe pair, ≥3:1 on white). Identity is also carried by the legend.
const C_OK = '#2747C9'
const C_ERR = '#C93C3C'

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  if (n >= 10_000) return `${Math.round(n / 1000)}K`
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}K`
  return String(Math.round(n))
}

function duration(ms: number): string {
  if (!ms) return '—'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`
}

function pct(part: number, whole: number): string {
  if (!whole) return '—'
  const v = (part / whole) * 100
  return `${v < 10 && v > 0 ? v.toFixed(1) : Math.round(v)}%`
}

export default function AdminMonitoringPage() {
  const { t, lang } = useLanguage()
  const [range, setRange] = useState<Range>('24h')
  const { data, isFetching, refetch, isError } = useQuery<MonitoringData>({
    queryKey: ['monitoring', range],
    queryFn: () => adminApi.monitoring(range),
    placeholderData: (prev) => prev, // keep the previous frame while refetching
    refetchInterval: 60_000,
  })

  const op = (o: string) => t(`op.${o}` as any)
  const locale = LOCALES[lang]

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">{t('mon.title')}</h1>
            <p className="mt-2 text-ink-muted max-w-xl">{t('mon.intro')}</p>
          </div>
          {data && (
            <Link to="/admin/ai" className="inline-flex items-center gap-2 text-sm text-ink-soft hover:text-ink">
              <Cpu size={15} />
              <span className="font-mono">{data.ai_config.model}</span>
              {!data.ai_config.has_key && <span className="text-bad font-semibold">· {t('mon.noKey')}</span>}
            </Link>
          )}
        </div>

        {/* Filters: one row above everything they scope */}
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <div role="group" aria-label={t('mon.range')} className="inline-flex rounded-lg bg-surface border border-line p-0.5 text-[13px] font-semibold">
            {(['24h', '7d', '30d'] as Range[]).map((r) => (
              <button key={r} onClick={() => setRange(r)} aria-pressed={range === r}
                className={`h-8 px-3 rounded-md transition-colors ${range === r ? 'bg-ink text-white' : 'text-ink-muted hover:text-ink'}`}>
                {t(`mon.range.${r}` as any)}
              </button>
            ))}
          </div>
          <button onClick={() => refetch()} className="btn-ghost btn-sm" disabled={isFetching}>
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} /> {t('mon.refresh')}
          </button>
          {data && (
            <span className="text-xs text-ink-muted">
              {t('mon.updated', { time: new Date(data.generated_at + 'Z').toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' }) })}
            </span>
          )}
        </div>

        {isError && <p role="alert" className="mt-6 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{t('mon.loadFailed')}</p>}

        {data && (
          <div className={`transition-opacity ${isFetching ? 'opacity-60' : ''}`}>
            {/* AI KPIs */}
            <section className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-3" aria-label={t('mon.aiSection')}>
              <Stat label={t('mon.aiCalls')} value={compact(data.ai.calls)} />
              <Stat label={t('mon.errorRate')} value={pct(data.ai.errors, data.ai.calls)}
                sub={t('mon.errorsN', { n: data.ai.errors })} warn={data.ai.calls > 0 && data.ai.errors / data.ai.calls > 0.05} />
              <Stat label={t('mon.latencyP95')} value={duration(data.ai.p95_ms)} sub={t('mon.median', { v: duration(data.ai.p50_ms) })} />
              <Stat label={t('mon.tokens')} value={compact(data.ai.input_tokens + data.ai.output_tokens)}
                sub={t('mon.tokensSplit', { i: compact(data.ai.input_tokens), o: compact(data.ai.output_tokens) })} />
            </section>

            {/* Activity */}
            <section className="mt-3 grid grid-cols-2 lg:grid-cols-4 gap-3" aria-label={t('mon.activity')}>
              <Stat label={t('mon.activeStudents')} value={compact(data.activity.active_students)} />
              <Stat label={t('mon.sessionsStarted')} value={compact(data.activity.sessions_started)} />
              <Stat label={t('mon.tasksCompleted')} value={compact(data.activity.tasks_completed)} />
              <Stat label={t('mon.stepsPassed')} value={`${compact(data.activity.steps_passed)} / ${compact(data.activity.step_checks)}`}
                sub={t('mon.passRate', { v: pct(data.activity.steps_passed, data.activity.step_checks) })} />
            </section>

            {/* Protection: code runner queue, per-student limits, refused requests */}
            <section className="mt-3 card px-4 py-3.5 grid sm:grid-cols-3 gap-x-6 gap-y-3 text-sm" aria-label={t('mon.protection')}>
              <div>
                <p className="text-[13px] text-ink-muted">{t('mon.runner')}</p>
                {data.runner ? (
                  <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-semibold">{t('mon.runnerBusy', { busy: data.runner.busy, workers: data.runner.workers })}</span>
                    <span className="text-ink-muted">· {t('mon.runnerWaiting', { n: data.runner.waiting })}</span>
                    {data.runner.isolated
                      ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-ok bg-ok-soft rounded-full px-2 py-0.5"><ShieldCheck size={12} /> {t('mon.isolated')}</span>
                      : <span className="inline-flex items-center gap-1 text-xs font-semibold text-bad bg-bad-soft rounded-full px-2 py-0.5"><AlertTriangle size={12} /> {t('mon.notIsolated')}</span>}
                  </p>
                ) : (
                  <p className="mt-1 font-semibold text-bad">{t('mon.runnerDown')}</p>
                )}
              </div>
              <div>
                <p className="text-[13px] text-ink-muted">{t('mon.limits')}</p>
                <p className="mt-1">{t('mon.limitsValue', { m: data.limits.ai_per_minute || '∞', d: data.limits.ai_per_day || '∞', tm: data.limits.tests_per_minute || '∞' })}</p>
              </div>
              <div>
                <p className="text-[13px] text-ink-muted">{t('mon.refused')}</p>
                <p className="mt-1"><span className="font-semibold">{compact(data.activity.rate_limited)}</span>
                  <span className="text-ink-muted"> · {t('mon.refusedStudents', { n: data.activity.rate_limited_students })}</span></p>
              </div>
            </section>

            {/* Timeline */}
            <section className="mt-6 card p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="font-bold">{t('mon.timelineTitle')}</h2>
                <div className="flex items-center gap-4 text-xs text-ink-soft">
                  <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: C_OK }} /> {t('mon.seriesOk')}</span>
                  <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: C_ERR }} /> {t('mon.seriesErr')}</span>
                </div>
              </div>
              <ColumnChart data={data} locale={locale} t={t} />
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer text-ink-muted hover:text-ink">{t('mon.asTable')}</summary>
                <div className="mt-2 max-h-64 overflow-auto">
                  <table className="w-full text-[13px] tabular-nums">
                    <thead><tr className="text-left text-ink-muted"><th className="py-1 font-medium">{t('mon.time')}</th><th className="font-medium text-right">{t('mon.seriesOk')}</th><th className="font-medium text-right">{t('mon.seriesErr')}</th><th className="font-medium text-right">{t('mon.testRuns')}</th></tr></thead>
                    <tbody>
                      {data.timeline.map((b) => (
                        <tr key={b.t} className="border-t border-line-soft">
                          <td className="py-1">{bucketLabel(b.t, data.bucket, locale, true)}</td>
                          <td className="text-right">{b.ai_ok}</td><td className="text-right">{b.ai_errors}</td><td className="text-right">{b.test_runs}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </section>

            <div className="mt-6 grid lg:grid-cols-2 gap-6">
              {/* By operation */}
              <section className="card p-5">
                <h2 className="font-bold">{t('mon.byOperation')}</h2>
                {data.ai_by_operation.length === 0 ? <Empty t={t} /> : (
                  <table className="mt-3 w-full text-[13px] tabular-nums">
                    <thead><tr className="text-left text-ink-muted">
                      <th className="py-1.5 font-medium">{t('mon.operation')}</th><th className="font-medium">{t('mon.calls')}</th>
                      <th className="font-medium text-right">{t('mon.errors')}</th><th className="font-medium text-right">p95</th><th className="font-medium text-right">{t('mon.tokensShort')}</th>
                    </tr></thead>
                    <tbody>
                      {data.ai_by_operation.map((r) => {
                        const max = Math.max(...data.ai_by_operation.map((x) => x.calls), 1)
                        return (
                          <tr key={r.operation} className="border-t border-line-soft">
                            <td className="py-2 pr-2 font-medium text-ink">{op(r.operation)}</td>
                            <td className="pr-3 w-[35%]">
                              <div className="flex items-center gap-2">
                                <div className="h-2 rounded-r" style={{ width: `${Math.max(4, (r.calls / max) * 100)}%`, background: C_OK }} aria-hidden />
                                <span>{compact(r.calls)}</span>
                              </div>
                            </td>
                            <td className={`text-right ${r.errors ? 'text-bad font-semibold' : 'text-ink-muted'}`}>{r.errors}</td>
                            <td className="text-right">{duration(r.p95_ms)}</td>
                            <td className="text-right">{compact(r.tokens)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </section>

              {/* By model */}
              <section className="card p-5">
                <h2 className="font-bold">{t('mon.byModel')}</h2>
                {data.ai_by_model.length === 0 ? <Empty t={t} /> : (
                  <table className="mt-3 w-full text-[13px] tabular-nums">
                    <thead><tr className="text-left text-ink-muted">
                      <th className="py-1.5 font-medium">{t('mon.model')}</th><th className="font-medium text-right">{t('mon.calls')}</th>
                      <th className="font-medium text-right">{t('mon.errors')}</th><th className="font-medium text-right">p95</th><th className="font-medium text-right">{t('mon.tokensInOut')}</th>
                    </tr></thead>
                    <tbody>
                      {data.ai_by_model.map((r) => (
                        <tr key={r.provider + r.model} className="border-t border-line-soft">
                          <td className="py-2 pr-2"><span className="font-mono text-[12.5px] text-ink">{r.model}</span><span className="block text-[11px] text-ink-muted">{r.provider}</span></td>
                          <td className="text-right">{compact(r.calls)}</td>
                          <td className={`text-right ${r.errors ? 'text-bad font-semibold' : 'text-ink-muted'}`}>{r.errors}</td>
                          <td className="text-right">{duration(r.p95_ms)}</td>
                          <td className="text-right">{compact(r.input_tokens)} / {compact(r.output_tokens)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>
            </div>

            {/* Tests by language */}
            <section className="mt-6 card p-5">
              <h2 className="font-bold">{t('mon.testsTitle')}</h2>
              <p className="text-[13px] text-ink-muted">{t('mon.testsHint')}</p>
              {data.tests_by_language.length === 0 ? <Empty t={t} /> : (
                <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {data.tests_by_language.map((r) => {
                    const passRate = r.tests_total ? r.tests_passed / r.tests_total : 0
                    return (
                      <div key={r.language} className="rounded-lg border border-line-soft p-4">
                        <div className="flex items-center justify-between">
                          <LangChip lang={r.language || 'cpp'} />
                          <span className="text-xs text-ink-muted">{t('mon.runsN', { n: r.runs })}</span>
                        </div>
                        <p className="mt-3 text-2xl font-bold tabular-nums">{pct(r.tests_passed, r.tests_total)}</p>
                        <p className="text-xs text-ink-muted">{t('mon.testsPassed', { p: compact(r.tests_passed), n: compact(r.tests_total) })}</p>
                        <div className="mt-2 h-1.5 rounded-full bg-ok-soft overflow-hidden" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(passRate * 100)}>
                          <div className="h-full bg-ok rounded-full" style={{ width: `${passRate * 100}%` }} />
                        </div>
                        <dl className="mt-3 grid grid-cols-2 gap-y-1 text-xs">
                          <dt className="text-ink-muted">{t('mon.allGreen')}</dt><dd className="text-right tabular-nums">{pct(r.all_green_runs, r.runs)}</dd>
                          <dt className="text-ink-muted">{t('mon.compileErrors')}</dt><dd className="text-right tabular-nums">{pct(r.runs_with_compile_errors, r.runs)}</dd>
                          <dt className="text-ink-muted">{t('mon.avgDuration')}</dt><dd className="text-right tabular-nums">{duration(r.avg_ms)}</dd>
                          {r.runner_errors > 0 && <><dt className="text-bad">{t('mon.runnerErrors')}</dt><dd className="text-right text-bad font-semibold">{r.runner_errors}</dd></>}
                        </dl>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>

            {/* Recent errors */}
            <section className="mt-6 card p-5">
              <h2 className="font-bold">{t('mon.recentErrors')}</h2>
              {data.recent_errors.length === 0 ? (
                <p className="mt-3 flex items-center gap-2 text-sm text-ok"><CheckCircle2 size={16} /> {t('mon.noErrors')}</p>
              ) : (
                <ul className="mt-3 divide-y divide-line-soft">
                  {data.recent_errors.map((e, i) => (
                    <li key={i} className="py-3 flex gap-3">
                      <AlertTriangle size={16} className="shrink-0 mt-0.5 text-bad" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm">
                          <span className="font-semibold">{op(e.operation)}</span>
                          <span className="text-ink-muted"> · {new Date(e.created_at + 'Z').toLocaleString(locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                          {e.model && <span className="text-ink-muted"> · <span className="font-mono text-[12px]">{e.model}</span></span>}
                        </p>
                        <p className="mt-1 font-mono text-[12px] text-ink-soft break-words">{e.error}</p>
                        {e.request_id && <p className="mt-0.5 text-[11px] text-ink-faint font-mono">request {e.request_id}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

function Stat({ label, value, sub, warn = false }: { label: string; value: string; sub?: string; warn?: boolean }) {
  return (
    <div className="card px-4 py-3.5">
      <p className="text-[13px] text-ink-muted">{label}</p>
      <p className={`mt-1 text-[26px] leading-tight font-semibold ${warn ? 'text-bad' : 'text-ink'}`}>
        {warn && <AlertTriangle size={18} className="inline -mt-1 mr-1" aria-label="!" />}
        {value}
      </p>
      {sub && <p className="text-xs text-ink-muted mt-0.5">{sub}</p>}
    </div>
  )
}

function Empty({ t }: { t: (k: any, p?: any) => string }) {
  return <p className="mt-3 text-sm text-ink-muted">{t('mon.empty')}</p>
}

function bucketLabel(iso: string, bucket: 'hour' | 'day', locale: string, long = false): string {
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  if (bucket === 'hour') {
    return long
      ? d.toLocaleString(locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
      : d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString(locale, { day: '2-digit', month: '2-digit' })
}

/** Stacked columns (successful + failed AI calls) per time bucket, with a per-column hover/focus tooltip. */
function ColumnChart({ data, locale, t }: { data: MonitoringData; locale: string; t: (k: any, p?: any) => string }) {
  const wrap = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(800)
  const [hover, setHover] = useState<number | null>(null)

  useEffect(() => {
    if (!wrap.current) return
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(280, e.contentRect.width)))
    ro.observe(wrap.current)
    return () => ro.disconnect()
  }, [])

  const H = 200, PAD_L = 34, PAD_B = 22, PAD_T = 8
  const pts = data.timeline
  const maxV = Math.max(1, ...pts.map((p) => p.ai_ok + p.ai_errors))
  const { top, ticks } = useMemo(() => {
    const step = Math.pow(10, Math.floor(Math.log10(maxV)))
    const nice = [1, 2, 5, 10].map((m) => m * step).find((s) => maxV / s <= 4) ?? step * 10
    const tp = Math.ceil(maxV / nice) * nice
    return { top: tp, ticks: Array.from({ length: Math.round(tp / nice) + 1 }, (_, i) => i * nice) }
  }, [maxV])

  const innerW = width - PAD_L
  const slot = innerW / Math.max(1, pts.length)
  const bw = Math.min(24, Math.max(3, slot * 0.62))
  const y = (v: number) => PAD_T + (H - PAD_T - PAD_B) * (1 - v / top)
  const labelEvery = Math.ceil(pts.length / Math.max(2, Math.floor(innerW / 64)))
  const empty = pts.every((p) => p.ai_ok + p.ai_errors === 0)

  return (
    <div ref={wrap} className="relative mt-4" onMouseLeave={() => setHover(null)}>
      <svg width={width} height={H} role="img" aria-label={t('mon.timelineTitle')}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={width} y1={y(v)} y2={y(v)} stroke="#E8EBF0" strokeWidth={1} />
            <text x={PAD_L - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill="#6B7488">{compact(v)}</text>
          </g>
        ))}
        {pts.map((p, i) => {
          const cx = PAD_L + slot * i + slot / 2
          const base = y(0)
          const hOk = base - y(p.ai_ok)
          const hErr = base - y(p.ai_errors)
          const gap = p.ai_ok && p.ai_errors ? 2 : 0
          const topSeg = p.ai_errors ? 'err' : 'ok'
          return (
            <g key={p.t} opacity={hover === null || hover === i ? 1 : 0.55}>
              {p.ai_ok > 0 && (
                <path d={colPath(cx - bw / 2, base - hOk, bw, hOk, topSeg === 'ok')} fill={C_OK} />
              )}
              {p.ai_errors > 0 && (
                <path d={colPath(cx - bw / 2, base - hOk - gap - hErr, bw, hErr, true)} fill={C_ERR} />
              )}
              {/* hit target: the whole slot, bigger than the mark */}
              <rect x={PAD_L + slot * i} y={PAD_T} width={slot} height={H - PAD_T - PAD_B} fill="transparent"
                tabIndex={0} aria-label={`${bucketLabel(p.t, data.bucket, locale, true)}: ${p.ai_ok} / ${p.ai_errors}`}
                onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
              {i % labelEvery === 0 && (
                <text x={cx} y={H - 6} textAnchor="middle" fontSize={11} fill="#6B7488">{bucketLabel(p.t, data.bucket, locale)}</text>
              )}
            </g>
          )
        })}
        <line x1={PAD_L} x2={width} y1={y(0)} y2={y(0)} stroke="#D9DEE7" strokeWidth={1} />
      </svg>
      {empty && <p className="absolute inset-x-0 top-16 text-center text-sm text-ink-muted">{t('mon.empty')}</p>}
      {hover !== null && pts[hover] && (
        <div className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg bg-surface shadow-lift border border-line px-3 py-2 text-xs"
          style={{ left: Math.min(width - 70, Math.max(70, PAD_L + slot * hover + slot / 2)), top: 0 }}>
          <p className="text-ink-muted">{bucketLabel(pts[hover].t, data.bucket, locale, true)}</p>
          <p className="mt-1 flex items-center gap-2"><span className="w-3 h-0.5" style={{ background: C_OK }} /><b className="tabular-nums">{pts[hover].ai_ok}</b> <span className="text-ink-muted">{t('mon.seriesOk')}</span></p>
          <p className="flex items-center gap-2"><span className="w-3 h-0.5" style={{ background: C_ERR }} /><b className="tabular-nums">{pts[hover].ai_errors}</b> <span className="text-ink-muted">{t('mon.seriesErr')}</span></p>
          <p className="mt-1 text-ink-muted">{t('mon.testRunsN', { n: pts[hover].test_runs })}</p>
        </div>
      )}
    </div>
  )
}

/** Column path: 4px rounded data-end (top) when `roundTop`, square at the baseline. */
function colPath(x: number, yTop: number, w: number, h: number, roundTop: boolean): string {
  if (h <= 0) return ''
  const r = roundTop ? Math.min(4, h, w / 2) : 0
  return `M${x},${yTop + h} V${yTop + r} Q${x},${yTop} ${x + r},${yTop} H${x + w - r} Q${x + w},${yTop} ${x + w},${yTop + r} V${yTop + h} Z`
}
