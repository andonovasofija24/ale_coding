import { Fragment, useEffect, useMemo, useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Activity, AlertTriangle, ChevronRight, Download, FlaskConical, Gauge, Loader2, Pause, Play, Search, ShieldCheck, Sparkles,
} from 'lucide-react'
import { logsApi, LogParams } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { LogItem, LogPage } from '../types'
import { formatDateTime, relative } from '../lib/time'

type Mode = 'admin' | 'course' | 'me'
type KindFilter = '' | 'ai' | 'tests' | 'activity' | 'errors'

const KIND_ICON: Record<LogItem['kind'], JSX.Element> = {
  ai: <Sparkles size={14} />, tests: <FlaskConical size={14} />, activity: <Activity size={14} />,
  limit: <Gauge size={14} />, audit: <ShieldCheck size={14} />,
}

/**
 * The logs: one line per AI call, test run or thing a person did, newest first. The admin sees everything (with
 * model, tokens and request id) and can export it; the course staff see the course (and the students' own practice
 * in its subject); everyone sees their own activity. "Live" refreshes every few seconds.
 */
export default function LogView({ mode, courseId, compact = false }: { mode: Mode; courseId?: string; compact?: boolean }) {
  const { t, lang } = useLanguage()
  const [kind, setKind] = useState<KindFilter>('')
  const [span, setSpan] = useState(mode === 'admin' ? '24h' : mode === 'course' ? '7d' : '30d')
  const [operation, setOperation] = useState('')
  const [q, setQ] = useState('')
  const [query, setQuery] = useState('')
  const [live, setLive] = useState(false)
  const [open, setOpen] = useState<number | null>(null)
  useEffect(() => { const id = setTimeout(() => setQuery(q), 350); return () => clearTimeout(id) }, [q])

  const params: LogParams = { kind: kind || undefined, span, operation: operation || undefined, q: query || undefined }
  const fetchPage = (before?: number) => {
    const p = { ...params, before }
    return mode === 'admin' ? logsApi.admin(p) : mode === 'course' ? logsApi.course(courseId!, p) : logsApi.mine(p)
  }
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage, isFetching } = useInfiniteQuery<LogPage>({
    queryKey: ['logs', mode, courseId, params],
    queryFn: ({ pageParam }) => fetchPage(pageParam as number | undefined),
    initialPageParam: undefined,
    getNextPageParam: (last) => last.next_before ?? undefined,
    refetchInterval: live ? 5000 : false,
  })
  const items = useMemo(() => (data?.pages ?? []).flatMap((p) => p.items), [data])
  const first = data?.pages[0]
  const totals = first?.totals
  const ops = first?.operations ?? []
  const showUser = mode !== 'me'

  return (
    <div>
      {/* filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={t('log.kind')}>
          {(['', 'ai', 'tests', 'activity', 'errors'] as KindFilter[]).map((k) => (
            <button key={k || 'all'} onClick={() => { setKind(k); setOperation('') }} aria-pressed={kind === k}
              className={`h-8 px-3 rounded-full text-[13px] font-semibold border-[1.5px] inline-flex items-center gap-1.5
                ${kind === k ? (k === 'errors' ? 'bg-bad text-white border-bad' : 'bg-ink text-white border-ink') : 'bg-surface border-line-strong text-ink-soft hover:border-ink'}`}>
              {k === 'errors' ? <AlertTriangle size={13} /> : k ? KIND_ICON[k] : null}
              {t(`log.k.${k || 'all'}` as any)}
              {totals && <span className="opacity-60 tabular-nums">{totals[k || 'all'] ?? 0}</span>}
            </button>
          ))}
        </div>
        <select className="input h-8 w-auto py-0 text-[13px]" value={span} onChange={(e) => setSpan(e.target.value)} aria-label={t('log.span')}>
          {['1h', '24h', '7d', '30d'].map((s) => <option key={s} value={s}>{t(`log.span.${s}` as any)}</option>)}
        </select>
        {mode === 'admin' && ops.length > 0 && (
          <select className="input h-8 w-auto max-w-[14rem] py-0 text-[13px]" value={operation} onChange={(e) => setOperation(e.target.value)} aria-label={t('log.operation')}>
            <option value="">{t('log.allOps')}</option>
            {ops.filter((o) => !kind || kind === 'errors' || o.kind === kind).map((o) =>
              <option key={o.operation} value={o.operation}>{opLabel(t, o.operation)} ({o.count})</option>)}
          </select>
        )}
        {mode !== 'me' && (
          <label className="relative flex-1 min-w-[12rem]">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint" />
            <input className="input h-8 pl-8 text-[13px]" value={q} onChange={(e) => setQ(e.target.value)}
              placeholder={t(mode === 'admin' ? 'log.searchAdmin' : 'log.searchCourse')} aria-label={t('log.search')} />
          </label>
        )}
        <button onClick={() => setLive((x) => !x)} aria-pressed={live}
          className={`h-8 px-3 rounded-lg text-[13px] font-semibold border inline-flex items-center gap-1.5 ${live ? 'bg-marker border-marker-deep/40' : 'bg-surface border-line-strong text-ink-soft hover:border-ink'}`}>
          {live ? <Pause size={13} /> : <Play size={13} />} {t('log.live')}
          {live && <span className="w-1.5 h-1.5 rounded-full bg-ink animate-pulse" aria-hidden />}
        </button>
        {mode === 'admin' && (
          <button className="btn-secondary h-8 text-[13px]" onClick={() => logsApi.csv(params)}><Download size={14} /> CSV</button>
        )}
      </div>

      {/* list */}
      <div className={`mt-4 card overflow-hidden ${compact ? '' : ''}`}>
        {isLoading ? <div className="py-12 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
          : items.length === 0 ? <p className="py-10 text-center text-[13.5px] text-ink-muted">{t('log.empty')}</p> : (
            <ol className="divide-y divide-line-soft" aria-busy={isFetching}>
              {items.map((x) => (
                <Fragment key={x.id}>
                  <li>
                    <button className={`w-full text-left grid gap-x-3 gap-y-0.5 px-4 py-2.5 hover:bg-paper/60 items-center
                      ${showUser ? 'grid-cols-[4.5rem_1.75rem_minmax(0,1fr)_auto] sm:grid-cols-[6.5rem_1.75rem_minmax(0,1.3fr)_minmax(0,1fr)_auto]' : 'grid-cols-[4.5rem_1.75rem_minmax(0,1fr)_auto] sm:grid-cols-[6.5rem_1.75rem_minmax(0,1fr)_auto]'}`}
                      aria-expanded={open === x.id} onClick={() => setOpen(open === x.id ? null : x.id)}>
                      <span className="text-[12px] text-ink-muted tabular-nums" title={formatDateTime(x.at, lang)}>{relative(x.at, lang)}</span>
                      <span className={`w-7 h-7 rounded-lg inline-flex items-center justify-center ${!x.ok ? 'bg-bad-soft text-bad' : x.kind === 'ai' ? 'bg-ink text-marker' : x.kind === 'tests' ? 'bg-marker-soft text-ink' : 'bg-line-soft text-ink-soft'}`}
                        aria-label={t(`log.k.${x.kind}` as any)}>{!x.ok ? <AlertTriangle size={14} /> : KIND_ICON[x.kind]}</span>
                      <span className="min-w-0">
                        <span className="block text-[13.5px] font-semibold truncate">
                          {opLabel(t, x.operation)}
                          {!x.ok && <span className="ml-2 text-[11.5px] font-bold text-bad">{t('log.failed')}</span>}
                        </span>
                        <span className="block text-[12px] text-ink-muted truncate">{summary(t, x)}</span>
                      </span>
                      {showUser && (
                        <span className="hidden sm:block min-w-0 text-[12.5px] truncate">
                          {x.user ? <><span className="font-medium">{x.user.name}</span> <span className="text-ink-muted">· {x.user.course_role ? t(`courseRole.${x.user.course_role}` as any) : t(`role.${x.user.role}` as any)}</span></> : <span className="text-ink-faint">—</span>}
                          {x.course && <span className="block text-[11.5px] text-ink-muted font-mono truncate">{x.course.code}</span>}
                        </span>
                      )}
                      <span className="flex items-center gap-2 text-[12px] text-ink-muted tabular-nums">
                        {x.duration_ms > 0 && <span>{fmtMs(x.duration_ms)}</span>}
                        <ChevronRight size={14} className={`text-ink-faint transition-transform ${open === x.id ? 'rotate-90' : ''}`} />
                      </span>
                    </button>
                  </li>
                  {open === x.id && <li className="bg-paper/60 px-4 py-3"><Details x={x} mode={mode} /></li>}
                </Fragment>
              ))}
            </ol>
          )}
      </div>
      {hasNextPage && (
        <div className="mt-3 flex justify-center">
          <button className="btn-secondary" disabled={isFetchingNextPage} onClick={() => fetchNextPage()}>
            {isFetchingNextPage && <Loader2 size={14} className="animate-spin" />} {t('log.more')}
          </button>
        </div>
      )}
    </div>
  )
}

function Details({ x, mode }: { x: LogItem; mode: Mode }) {
  const { t, lang } = useLanguage()
  const rows: [string, React.ReactNode][] = [
    [t('log.d.time'), formatDateTime(x.at, lang)],
    [t('log.d.kind'), `${t(`log.k.${x.kind}` as any)} · ${x.operation}`],
  ]
  if (x.user) rows.push([t('log.d.user'), `${x.user.name} · ${x.user.email}`])
  if (x.task) rows.push([t('log.d.task'), <Link key="t" to={`/tasks/${x.task.id}`} className="text-cobalt hover:underline">{x.task.title}</Link>])
  if (x.course) rows.push([t('log.d.course'), <Link key="c" to={`/courses/${x.course.id}`} className="text-cobalt hover:underline">{x.course.code} · {x.course.name}</Link>])
  if (x.language) rows.push([t('log.d.language'), x.language])
  if (x.duration_ms) rows.push([t('log.d.duration'), fmtMs(x.duration_ms)])
  if (mode === 'admin') {
    if (x.model) rows.push([t('log.d.model'), `${x.provider ?? ''} · ${x.model}`])
    if (x.input_tokens || x.output_tokens) rows.push([t('log.d.tokens'), `${x.input_tokens} → ${x.output_tokens}`])
    if (x.request_id) rows.push([t('log.d.request'), <span key="r" className="font-mono">{x.request_id}</span>])
  }
  const extra = Object.entries(x.extra || {})
  return (
    <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1.5 text-[12.5px]">
      <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1">
        {rows.map(([k, v]) => <Fragment key={k}><dt className="text-ink-muted">{k}</dt><dd className="min-w-0 break-words">{v}</dd></Fragment>)}
      </dl>
      <div className="min-w-0">
        {extra.length > 0 && (
          <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1">
            {extra.map(([k, v]) => <Fragment key={k}><dt className="text-ink-muted font-mono">{k}</dt><dd className="font-mono break-all">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd></Fragment>)}
          </dl>
        )}
        {x.error && <p className="mt-2 rounded-lg bg-bad-soft text-bad px-3 py-2 font-mono text-[12px] whitespace-pre-wrap break-words">{x.error}</p>}
      </div>
    </div>
  )
}

const fmtMs = (ms: number) => ms >= 1000 ? `${(ms / 1000).toFixed(ms >= 10000 ? 0 : 1)} s` : `${ms} ms`

export function opLabel(t: (k: any, v?: any) => string, op: string): string {
  const k = `log.op.${op}`
  const s = t(k)
  return s === k ? op.replace(/_/g, ' ') : s
}

/** One line under the operation: what it was about, from its details. */
function summary(t: (k: any, v?: any) => string, x: LogItem): string {
  const e = x.extra || {}
  const bits: string[] = []
  if (x.about) bits.push(`→ ${x.about}`)
  if (x.task) bits.push(x.task.title)
  else if (e.title) bits.push(String(e.title))
  if (e.total != null && e.passed != null) bits.push(t('log.s.tests', { p: e.passed, t: e.total }))
  if (e.override != null) bits.push(t('log.s.points', { n: e.override }))
  if (e.grade != null) bits.push(t('log.s.grade', { n: e.grade }))
  else if (x.operation === 'final_grade') bits.push(t('log.s.gradeCleared'))
  if (e.step != null) bits.push(t('log.s.step', { n: e.step }))
  if (e.semester != null) bits.push(t('log.s.semester', { n: e.semester }))
  if (e.role) bits.push(t(`courseRole.${e.role}` as any))
  if (e.new) bits.push(`${e.old ?? ''} → ${e.new}`)
  if (e.added != null) bits.push(t('log.s.added', { n: e.added }))
  if (e.status && x.operation === 'attendance') bits.push(t(`att.${e.status}` as any))
  else if (e.status && x.operation !== 'submit') bits.push(String(e.status))
  if (e.language && !x.language) bits.push(String(e.language))
  if (e.email) bits.push(String(e.email))
  if (e.code && !e.title) bits.push(`${e.code}${e.name ? ' · ' + e.name : ''}`)
  if (e.message) bits.push(String(e.message).replace('Lti', ''))
  if (x.kind === 'ai' && (x.input_tokens || x.output_tokens)) bits.push(`${(x.input_tokens ?? 0) + (x.output_tokens ?? 0)} tok.`)
  if (!x.ok && x.error) bits.push(x.error.slice(0, 90))
  return bits.join(' · ') || '—'
}
