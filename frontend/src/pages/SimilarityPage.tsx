import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Columns2, GraduationCap, Info, Loader2 } from 'lucide-react'
import { assignmentsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { Assignment, SimilarityReport } from '../types'
import AppHeader from '../components/AppHeader'
import LangChip from '../components/LangChip'
import CodeView from '../components/course/CodeView'
import DiagramEditor from '../components/DiagramEditor'
import { WebSubmissionView } from '../components/WebWorkspace'
import { diagramKindOf } from '../lib/diagram'

type Pair = SimilarityReport['tasks'][number]['pairs'][number]

/** Staff: pairs of structurally similar solutions per task, and a side-by-side view with the matching parts marked. */
export default function SimilarityPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const { t } = useLanguage()
  const [threshold, setThreshold] = useState(0.7)
  const [open, setOpen] = useState<{ task: string; pair: Pair } | null>(null)
  const { data: a } = useQuery<Assignment>({ queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!) })
  const { data, isFetching } = useQuery<SimilarityReport>({
    queryKey: ['similarity', assignmentId, threshold], queryFn: () => assignmentsApi.similarity(assignmentId!, threshold),
  })

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <Link to={`/assignments/${assignmentId}`} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {a?.title ?? t('common.loading')}
        </Link>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[16rem]">
            <h1 className="text-3xl font-extrabold tracking-tight">{t('sim.title')}</h1>
            <p className="mt-1 text-sm text-ink-muted max-w-2xl">{t('sim.hint')}</p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm">
            {t('sim.threshold')}
            <select className="input h-9 w-auto" value={threshold} onChange={(e) => { setThreshold(parseFloat(e.target.value)); setOpen(null) }}>
              {[0.5, 0.6, 0.7, 0.8, 0.9].map((v) => <option key={v} value={v}>≥ {Math.round(v * 100)}%</option>)}
            </select>
          </label>
          <Link to={`/assignments/${assignmentId}/grading`} className="btn-secondary"><GraduationCap size={15} /> {t('grading.open')}</Link>
        </div>
        <p className="mt-4 flex items-start gap-2 text-[13px] text-ink-soft bg-surface border border-line rounded-lg px-3.5 py-2.5 max-w-3xl">
          <Info size={15} className="shrink-0 mt-0.5 text-cobalt" /> {t('sim.caution')}
        </p>

        {!data ? (
          <div className="flex justify-center py-16 text-ink-muted"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className={`mt-6 space-y-6 ${isFetching ? 'opacity-60' : ''}`}>
            {data.tasks.map((task) => (
              <section key={task.task_id}>
                <h2 className="flex flex-wrap items-center gap-2 font-bold">
                  <LangChip lang={task.language} /> {task.title}
                  <span className="text-[13px] font-normal text-ink-muted">· {t('sim.compared', { n: task.compared })}</span>
                </h2>
                {task.pairs.length === 0 ? (
                  <p className="mt-2 card px-4 py-5 text-sm text-ink-muted">{task.compared < 2 ? t('sim.tooFew') : t('sim.none')}</p>
                ) : (
                  <ul className="mt-2 card divide-y divide-line-soft overflow-hidden">
                    {task.pairs.map((p) => {
                      const on = open?.task === task.task_id && open.pair.a.submission_id === p.a.submission_id && open.pair.b.submission_id === p.b.submission_id
                      return (
                        <li key={`${p.a.user_id}-${p.b.user_id}`}>
                          <button onClick={() => setOpen(on ? null : { task: task.task_id, pair: p })}
                            className={`w-full flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-left ${on ? 'bg-marker-soft/60' : 'hover:bg-paper/60'}`}>
                            <Score v={p.similarity} />
                            <span className="min-w-0 flex-1 text-sm">
                              <span className="font-semibold">{p.a.name}</span>
                              <span className="text-ink-muted"> ↔ </span>
                              <span className="font-semibold">{p.b.name}</span>
                              {p.layout != null && (
                                <span className="ml-2 text-[12px] text-ink-muted">· {t('sim.layout', { n: Math.round(p.layout * 100) })}</span>
                              )}
                            </span>
                            <span className="inline-flex items-center gap-1 text-[13px] text-cobalt font-semibold"><Columns2 size={14} /> {t('sim.compare')}</span>
                          </button>
                          {on && <SideBySide pair={p} web={task.language === 'web'} />}
                        </li>
                      )
                    })}
                  </ul>
                )}
              </section>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function Score({ v }: { v: number }) {
  const pct = Math.round(v * 100)
  const tone = pct >= 90 ? 'bg-bad' : pct >= 75 ? 'bg-marker-deep' : 'bg-ink-faint'
  return (
    <span className="inline-flex items-center gap-2 w-36">
      <span className="h-2 flex-1 rounded-full bg-line-soft overflow-hidden" aria-hidden>
        <span className={`block h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </span>
      <span className="text-sm font-bold tabular-nums w-10 text-right">{pct}%</span>
    </span>
  )
}

function SideBySide({ pair, web = false }: { pair: Pair; web?: boolean }) {
  const { t } = useLanguage()
  const qa = useQuery({ queryKey: ['submission', pair.a.submission_id], queryFn: () => assignmentsApi.submission(pair.a.submission_id) })
  const qb = useQuery({ queryKey: ['submission', pair.b.submission_id], queryFn: () => assignmentsApi.submission(pair.b.submission_id) })
  if (!qa.data || !qb.data) return <div className="py-6 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
  const kind = diagramKindOf(qa.data.code) ?? diagramKindOf(qb.data.code)
  const sides = [{ who: pair.a, code: qa.data.code, lines: pair.lines_a }, { who: pair.b, code: qb.data.code, lines: pair.lines_b }]
  if (kind) {
    return (
      <div className="px-4 pb-4 bg-paper/40">
        <div className="pt-3 pb-2 space-y-2 text-[13px]">
          {pair.layout != null && (
            <p className="text-ink-soft"><span className="font-semibold text-ink">{t('sim.layout', { n: Math.round(pair.layout * 100) })}</span> — {t('sim.layoutHint')}</p>
          )}
          <div>
            <p className="font-semibold">{t('sim.shared')}</p>
            {pair.shared && pair.shared.length > 0 ? (
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {pair.shared.map((x) => <li key={x} className="px-2 py-0.5 rounded-md bg-marker-soft border border-marker/60 text-[12px] font-medium">{x}</li>)}
              </ul>
            ) : <p className="text-ink-muted">{t('sim.sharedNone')}</p>}
            <p className="mt-1 text-[12px] text-ink-muted">{t('sim.sharedHint')}</p>
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {sides.map((x) => (
            <div key={x.who.user_id} className="min-w-0">
              <p className="mb-1 text-[13px] font-semibold truncate">{x.who.name} <span className="font-normal text-ink-muted">· {x.who.email}</span></p>
              <div className="card overflow-hidden h-[26rem]"><DiagramEditor code={x.code} kind={diagramKindOf(x.code) ?? kind} readOnly /></div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="px-4 pb-4 bg-paper/40">
      <p className="pt-3 pb-2 text-[12px] text-ink-muted flex items-center gap-2">
        <span className="inline-block w-3 h-3 rounded-sm bg-marker-soft border border-marker" /> {t('sim.legend')}
      </p>
      <div className="grid md:grid-cols-2 gap-3">
        {sides.map((x) => (
          <div key={x.who.user_id} className="min-w-0">
            <p className="mb-1 text-[13px] font-semibold truncate">{x.who.name} <span className="font-normal text-ink-muted">· {x.who.email}</span></p>
            {web ? <WebSubmissionView code={x.code} height="24rem"><CodeView code={x.code} highlight={x.lines} maxHeight="28rem" /></WebSubmissionView>
              : <CodeView code={x.code} highlight={x.lines} maxHeight="28rem" />}
          </div>
        ))}
      </div>
    </div>
  )
}
