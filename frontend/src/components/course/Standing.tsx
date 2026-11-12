import { Fragment, useState } from 'react'
import { can } from '../../lib/perms'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Check, ChevronDown, FileSpreadsheet, Loader2, Minus, X } from 'lucide-react'
import { standingApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { CourseDetail, CourseStanding, GradeCategory, GradeEstimate, GradingScheme, StandingReason, StudentStanding } from '../../types'
import { CATEGORIES } from './GradingSchemeCard'
import { fmt } from './bits'

/** The reason for a "no", in words. */
export function useReason() {
  const { t } = useLanguage()
  return (r: StandingReason) => t(`reason.${r.key}` as any, {
    ...r, K: r.k ? t(`gcat.${r.k}` as any) : '', got: r.got != null ? fmt(Number(r.got)) : '', need: r.need != null ? fmt(Number(r.need)) : '',
  })
}

function YesNo({ v, label }: { v: boolean | null; label: string }) {
  const { t } = useLanguage()
  if (v == null) return <span className="text-ink-faint" title={t('standing.noRule')}><Minus size={14} className="inline" /></span>
  return v
    ? <span className="inline-flex items-center gap-1 text-ok font-semibold" title={label}><Check size={14} /> <span className="sr-only">{t('standing.yes')}</span></span>
    : <span className="inline-flex items-center gap-1 text-bad font-semibold" title={label}><X size={14} /> <span className="sr-only">{t('standing.no')}</span></span>
}

const weighted = (s: GradingScheme) => CATEGORIES.filter((c) => (s.weights[c] ?? 0) > 0)
const pct = (v: number | null) => (v == null ? '—' : `${fmt(v)}%`)

/** Staff: each student's standing under the course's rules, and the Excel grade sheet. */
export function StandingTable({ course, group }: { course: CourseDetail; group: string }) {
  const { t } = useLanguage()
  const reason = useReason()
  const { data, isLoading } = useQuery<CourseStanding>({ queryKey: ['standing', course.id], queryFn: () => standingApi.standing(course.id) })
  const [open, setOpen] = useState<string | null>(null)
  if (isLoading || !data) return <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>
  const cats = weighted(data.scheme)
  const students = data.students.filter((s) => !group || s.group === group)
  const rulesOn = data.scheme.rules.filter((r) => r.enabled).length
  const graded = students.filter((s) => s.grade != null)
  return (
    <div>
      <p className="mt-4 text-[13px] text-ink-muted">
        {t('standing.summary', {
          w: cats.map((c) => `${t(`gcat.${c}` as any)} ${fmt(data.scheme.weights[c])}%`).join(' · '),
          r: rulesOn,
        })}
        {can(course, 'grades.rules') && <> {t('standing.changeBelow')}</>}
      </p>
      {students.length === 0 ? <div className="mt-4 card px-6 py-12 text-center text-ink-muted">{t('grades.noStudents')}</div> : (
        <div className="mt-3 card overflow-x-auto">
          <table className="w-full text-sm border-separate border-spacing-0">
            <thead>
              <tr className="text-[12px] text-ink-muted">
                <th className="sticky left-0 z-10 bg-surface text-left px-4 py-2.5 font-semibold border-b border-line-soft min-w-[10rem]">{t('course.name')}</th>
                {cats.map((c) => <th key={c} className="px-3 py-2.5 font-semibold border-b border-line-soft text-right">{t(`gcat.${c}` as any)}<span className="block font-normal">{fmt(data.scheme.weights[c])}%</span></th>)}
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-right">{t('standing.total')}</th>
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-center">{t('standing.missed')}</th>
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-center">{t('standing.signature')}</th>
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-center">{t('standing.eligible')}</th>
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-center">{t('standing.exempt')}</th>
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-center">{t('standing.proposal')}</th>
                <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-center" title={t('est.hintStaff')}>{t('est.short')}</th>
                <th className="sticky right-0 z-10 bg-surface px-4 py-2.5 font-semibold border-b border-l border-line-soft text-center" title={t('standing.finalHint')}>{t('standing.grade')}</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => {
                const shown = s.reasons.filter((r) => r.key !== 'incomplete')
                return (
                  <Fragment key={s.user_id}>
                    <tr className="hover:bg-paper/50">
                      <td className="sticky left-0 z-10 bg-surface px-4 py-2 border-b border-line-soft">
                        <button className="text-left w-full group" onClick={() => setOpen(open === s.user_id ? null : s.user_id)} aria-expanded={open === s.user_id}>
                          <span className="flex items-center gap-1 font-medium truncate max-w-[14rem]">
                            {s.name}
                            {shown.length > 0 && <AlertCircle size={13} className="text-bad shrink-0" aria-label={t('standing.hasReasons')} />}
                            <ChevronDown size={13} className={`text-ink-faint shrink-0 transition-transform ${open === s.user_id ? 'rotate-180' : ''}`} />
                          </span>
                          <span className="block text-[12px] text-ink-muted truncate max-w-[14rem]">{[s.index, s.group].filter(Boolean).join(' · ') || s.email}</span>
                        </button>
                      </td>
                      {cats.map((c) => (
                        <td key={c} className={`px-3 py-2 border-b border-line-soft text-right tabular-nums ${s.colloquia[c]?.passed === false ? 'text-bad font-semibold' : ''}`}>
                          {pct(s.categories[c].pct)}
                        </td>
                      ))}
                      <td className="px-3 py-2 border-b border-line-soft text-right font-bold tabular-nums">{fmt(s.total)}%</td>
                      <td className={`px-3 py-2 border-b border-line-soft text-center tabular-nums ${s.missed_labs > 0 ? 'text-bad' : 'text-ink-muted'}`}>{s.missed_labs}</td>
                      <td className="px-3 py-2 border-b border-line-soft text-center"><YesNo v={s.signature} label={t('standing.signature')} /></td>
                      <td className="px-3 py-2 border-b border-line-soft text-center"><YesNo v={s.eligible_exam} label={t('standing.eligible')} /></td>
                      <td className="px-3 py-2 border-b border-line-soft text-center"><YesNo v={s.exempt} label={t('standing.exempt')} /></td>
                      <td className="px-3 py-2 border-b border-line-soft text-center">
                        {s.grade != null ? <span className={`inline-flex w-7 h-7 items-center justify-center rounded-full font-bold ${s.grade >= 6 ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{s.grade}</span>
                          : <span className="text-ink-faint" title={t('reason.incomplete')}>—</span>}
                      </td>
                      <td className="px-3 py-2 border-b border-line-soft text-center tabular-nums text-ink-soft" title={s.estimate?.total != null ? `${fmt(s.estimate.total)}%` : t('est.notYet')}>
                        {s.estimate?.grade != null ? <span className="inline-flex w-7 h-7 items-center justify-center rounded-full border-2 border-dashed border-ink/40 font-bold">{s.estimate.grade}</span> : '—'}
                      </td>
                      <td className="sticky right-0 z-10 bg-surface px-4 py-2 border-b border-l border-line-soft text-center">
                        <FinalGrade courseId={course.id} student={s} canSet={can(course, 'grades.final')} />
                      </td>
                    </tr>
                    {open === s.user_id && (
                      <tr>
                        <td colSpan={cats.length + 8} className="px-4 py-3 border-b border-line-soft bg-paper/60 text-[13px]">
                          {s.reasons.length === 0 ? <span className="text-ok">{t('standing.allGood')}</span> : (
                            <ul className="list-disc pl-5 space-y-0.5">{s.reasons.map((r, i) => <li key={i} className={r.key === 'incomplete' ? 'text-ink-muted' : ''}>{reason(r)}</li>)}</ul>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-[12px] text-ink-muted">
        {t('standing.legend', { n: graded.length, all: students.length })}
      </p>
    </div>
  )
}

export function ExcelButton({ course, group }: { course: CourseDetail; group: string }) {
  const { t } = useLanguage()
  const [busy, setBusy] = useState(false)
  return (
    <button className="btn-secondary" disabled={busy} title={t('standing.excelHint')}
      onClick={async () => { setBusy(true); try { await standingApi.downloadSheet(course.id, group || undefined) } finally { setBusy(false) } }}>
      {busy ? <Loader2 size={15} className="animate-spin" /> : <FileSpreadsheet size={15} />} {t('standing.excel')}
    </button>
  )
}

/** Student: "my standing" — points per part, signature, eligibility, the proposed grade and why. */
export function MyStanding({ courseId }: { courseId: string }) {
  const { t } = useLanguage()
  const reason = useReason()
  const { data, isLoading } = useQuery<{ scheme: GradingScheme; me: StudentStanding | null }>({
    queryKey: ['standing', courseId, 'me'], queryFn: () => standingApi.standing(courseId),
  })
  if (isLoading || !data) return <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>
  const me = data.me
  if (!me) return <div className="card px-6 py-12 text-center text-ink-muted">{t('standing.none')}</div>
  const cats = weighted(data.scheme)
  const rule = (type: string) => data.scheme.rules.find((r) => r.type === type && r.enabled)
  const badges: { label: string; v: boolean | null }[] = [
    { label: t('standing.signature'), v: me.signature },
    { label: t('standing.eligible'), v: rule('signature_for_exam') ? me.eligible_exam : null },
    { label: t('standing.exempt'), v: me.exempt },
  ].filter((b) => b.v != null)

  return (
    <div className="space-y-4">
      {me.estimate && <EstimateCard e={me.estimate} weights={data.scheme.weights} final={me.final_grade ?? null} />}
      <section className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-end gap-6">
          <div>
            <p className="panel-title">{t('standing.total')}</p>
            <p className="text-4xl font-extrabold tabular-nums">{fmt(me.total)}<span className="text-xl text-ink-muted">%</span></p>
          </div>
          {me.final_grade != null && (
            <div>
              <p className="panel-title">{t('standing.grade')}</p>
              <p className="text-4xl font-extrabold">{me.final_grade}</p>
            </div>
          )}
          <div>
            <p className="panel-title">{t('standing.proposed')}</p>
            <p className={`text-4xl font-extrabold ${me.grade == null ? 'text-ink-faint' : me.grade >= 6 ? 'text-ok' : 'text-bad'}`}>{me.grade ?? '—'}</p>
          </div>
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-2 ml-auto">
              {badges.map((b) => (
                <span key={b.label} className={`inline-flex items-center gap-1.5 text-[13px] font-semibold rounded-full px-3 py-1 ${b.v ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>
                  {b.v ? <Check size={14} /> : <X size={14} />} {b.label}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="mt-5 grid gap-3">
          {cats.map((c: GradeCategory) => {
            const v = me.categories[c]
            const p = v.pct ?? 0
            return (
              <div key={c}>
                <div className="flex justify-between text-[13px]">
                  <span className="font-semibold">{t(`gcat.${c}` as any)} <span className="text-ink-muted font-normal">· {t('standing.weight', { n: fmt(data.scheme.weights[c]) })}</span></span>
                  <span className="tabular-nums text-ink-soft">{v.max ? `${fmt(v.got)} / ${fmt(v.max)} · ${pct(v.pct)}` : t('standing.notYet')}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-line-soft overflow-hidden" role="progressbar" aria-valuenow={p} aria-valuemin={0} aria-valuemax={100} aria-label={t(`gcat.${c}` as any)}>
                  <div className={`h-full rounded-full ${me.colloquia[c]?.passed === false ? 'bg-bad' : 'bg-cobalt'}`} style={{ width: `${Math.min(100, p)}%` }} />
                </div>
              </div>
            )
          })}
        </div>
        {me.reasons.length > 0 && (
          <ul className="mt-5 space-y-1 text-[13px]">
            {me.reasons.map((r, i) => (
              <li key={i} className={`flex items-start gap-2 ${r.key === 'incomplete' ? 'text-ink-muted' : 'text-bad'}`}>
                <AlertCircle size={14} className="mt-0.5 shrink-0" /> {reason(r)}
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="text-[12px] text-ink-muted">{t('standing.studentNote', { th: data.scheme.thresholds.map((x, i) => `${6 + i}: ${fmt(x)}%`).join(' · ') })}</p>
    </div>
  )
}


/** The final grade (5–10): only the professor enters it; the proposal next to it is only a suggestion. */
function FinalGrade({ courseId, student, canSet }: { courseId: string; student: { user_id: string; name: string; grade: number | null; final_grade?: number | null }; canSet: boolean }) {
  const { t } = useLanguage()
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  const v = student.final_grade ?? null
  if (!canSet) return v != null ? <span className="inline-flex w-7 h-7 items-center justify-center rounded-full font-extrabold bg-ink text-white">{v}</span>
    : <span className="text-ink-faint">—</span>
  return (
    <select aria-label={t('standing.finalFor', { name: student.name })} disabled={busy}
      className={`input h-8 w-[4.25rem] px-2 text-[13px] font-bold text-center ${v != null ? 'bg-ink text-white border-ink' : ''}`}
      value={v ?? ''} onChange={async (e) => {
        setBusy(true)
        try { await standingApi.setFinal(courseId, student.user_id, e.target.value ? parseInt(e.target.value) : null); qc.invalidateQueries({ queryKey: ['standing', courseId] }) }
        finally { setBusy(false) }
      }}>
      <option value="">{student.grade != null ? `(${student.grade})` : '—'}</option>
      {[5, 6, 7, 8, 9, 10].map((g) => <option key={g} value={g}>{g}</option>)}
    </select>
  )
}


/** "If you keep going like this": the grade from the course's rules, with the parts that have no points yet taken
 *  from what the student practised (colloquium exercises, labs still open, their own practice in the subject). */
function EstimateCard({ e, weights, final }: { e: GradeEstimate; weights: Record<string, number>; final: number | null }) {
  const { t } = useLanguage()
  if (final != null) return null
  const parts = Object.entries(e.parts) as [GradeCategory, { pct: number | null; source: string | null }][]
  return (
    <section className="rounded-xl bg-ink text-white p-5 sm:p-6">
      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div>
          <p className="text-[12px] text-white/60">{t('est.title')}</p>
          <p className="text-5xl font-extrabold leading-none mt-1">{e.grade ?? '—'}</p>
        </div>
        <p className="text-[13px] text-white/70 flex-1 min-w-[14rem]">{e.grade != null ? t('est.hint', { total: fmt(e.total ?? 0) }) : t('est.notYetHint')}</p>
      </div>
      <ul className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {parts.map(([c, v]) => (
          <li key={c} className="rounded-lg bg-white/[.07] px-3 py-2">
            <p className="flex items-baseline justify-between gap-2 text-[13px]"><span className="font-semibold">{t(`gcat.${c}` as any)} <span className="text-white/50 font-normal">{fmt(weights[c] ?? 0)}%</span></span>
              <span className="font-bold tabular-nums">{v.pct == null ? '—' : `${fmt(v.pct)}%`}</span></p>
            <p className="text-[11.5px] text-marker">{v.source ? t(`est.src.${v.source}` as any) : t('est.src.none')}</p>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11.5px] text-white/50">{t('est.note')}</p>
    </section>
  )
}
