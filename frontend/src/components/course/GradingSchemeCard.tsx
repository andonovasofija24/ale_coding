import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Save, Scale } from 'lucide-react'
import { standingApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { GradeCategory, GradingScheme, RuleType } from '../../types'

export const CATEGORIES: GradeCategory[] = ['labs', 'homework', 'k1', 'k2', 'exam']
const UNIT: Record<RuleType, string> = {
  max_missed_labs: '', min_labs_signature: '%', min_colloquium: '%', k1_exempt_qualifying: '%', signature_for_exam: '',
}

/** Teacher: what the final grade is made of (weights), the % for each grade, and the course's rules (each on/off). */
export default function GradingSchemeCard({ courseId, readOnly = false }: { courseId: string; readOnly?: boolean }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const { data } = useQuery<GradingScheme>({ queryKey: ['grading', courseId], queryFn: () => standingApi.scheme(courseId) })
  const [f, setF] = useState<GradingScheme | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => { if (data) setF(structuredClone(data)) }, [data])

  if (!f) return <section className="card p-6 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></section>

  const sum = CATEGORIES.reduce((n, c) => n + (Number(f.weights[c]) || 0), 0)
  const thOk = f.thresholds.every((x, i) => x > 0 && x <= 100 && (i === 0 || x > f.thresholds[i - 1]))
  const setRule = (type: RuleType, patch: object) =>
    setF({ ...f, rules: f.rules.map((r) => (r.type === type ? { ...r, ...patch } : r)) })

  const save = async () => {
    setSaving(true); setMsg(null)
    try {
      await standingApi.saveScheme(courseId, f)
      qc.invalidateQueries({ queryKey: ['grading', courseId] })
      qc.invalidateQueries({ queryKey: ['standing', courseId] })
      setMsg({ ok: true, text: t('course.saved') })
    } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'course.actionFailed') })
    } finally { setSaving(false) }
  }

  return (
    <section className="card p-5 sm:p-6">
      <h2 className="font-bold flex items-center gap-2"><Scale size={17} /> {t('scheme.title')}</h2>
      <p className="mt-1 text-[13px] text-ink-muted">{t('scheme.hint')}</p>

      {/* weights */}
      <h3 className="panel-title mt-5 mb-2">{t('scheme.weights')}</h3>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {CATEGORIES.map((c) => (
          <label key={c} className="rounded-lg border border-line px-3 py-2">
            <span className="block text-[12px] font-semibold text-ink-muted">{t(`gcat.${c}` as any)}</span>
            <span className="flex items-baseline gap-1">
              <input type="number" min={0} max={100} step={1} disabled={readOnly} value={f.weights[c]}
                onChange={(e) => setF({ ...f, weights: { ...f.weights, [c]: Number(e.target.value) } })}
                className="w-full bg-transparent text-lg font-bold tabular-nums focus:outline-none" aria-label={t(`gcat.${c}` as any)} />
              <span className="text-ink-muted text-sm">%</span>
            </span>
          </label>
        ))}
      </div>
      <p className={`mt-1.5 text-[12px] tabular-nums ${sum === 100 ? 'text-ink-muted' : 'text-bad font-semibold'}`}>
        {t('scheme.sum', { n: sum })}
      </p>

      {/* thresholds */}
      <h3 className="panel-title mt-5 mb-2">{t('scheme.thresholds')}</h3>
      <div className="flex flex-wrap gap-2">
        {f.thresholds.map((th, i) => (
          <label key={i} className="rounded-lg border border-line px-3 py-2 w-[6.5rem]">
            <span className="block text-[12px] font-semibold text-ink-muted">{t('scheme.gradeN', { n: 6 + i })}</span>
            <span className="flex items-baseline gap-1">
              <span className="text-ink-muted text-sm">≥</span>
              <input type="number" min={1} max={100} disabled={readOnly} value={th}
                onChange={(e) => setF({ ...f, thresholds: f.thresholds.map((x, j) => (j === i ? Number(e.target.value) : x)) })}
                className="w-full bg-transparent text-lg font-bold tabular-nums focus:outline-none" aria-label={t('scheme.gradeN', { n: 6 + i })} />
              <span className="text-ink-muted text-sm">%</span>
            </span>
          </label>
        ))}
      </div>
      {!thOk && <p className="mt-1.5 text-[12px] text-bad font-semibold">{t('scheme.thresholdsBad')}</p>}

      {/* rules */}
      <h3 className="panel-title mt-5 mb-2">{t('scheme.rules')}</h3>
      <div className="rounded-lg border border-line overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-[12px] text-ink-muted">
            <tr>
              <th className="text-left px-3 py-2 font-semibold w-16">{t('scheme.applies')}</th>
              <th className="text-left px-3 py-2 font-semibold">{t('scheme.rule')}</th>
              <th className="text-right px-3 py-2 font-semibold w-28">{t('scheme.value')}</th>
            </tr>
          </thead>
          <tbody>
            {f.rules.map((r) => (
              <tr key={r.type} className={`border-t border-line-soft ${r.enabled ? '' : 'text-ink-muted'}`}>
                <td className="px-3 py-2.5">
                  <input type="checkbox" className="w-4 h-4 accent-cobalt" checked={r.enabled} disabled={readOnly}
                    onChange={(e) => setRule(r.type, { enabled: e.target.checked })} aria-label={t(`rule.${r.type}` as any)} />
                </td>
                <td className="px-3 py-2.5">
                  <span className={r.enabled ? 'font-medium' : ''}>{t(`rule.${r.type}` as any)}</span>
                  <span className="block text-[12px] text-ink-muted">{t(`rule.${r.type}.hint` as any)}</span>
                </td>
                <td className="px-3 py-2.5 text-right">
                  {r.type === 'signature_for_exam' ? <span className="text-ink-faint">—</span> : (
                    <span className="inline-flex items-baseline gap-1">
                      <input type="number" min={0} max={r.type === 'max_missed_labs' ? 10 : 100} disabled={readOnly || !r.enabled}
                        value={r.value ?? 0} onChange={(e) => setRule(r.type, { value: Number(e.target.value) })}
                        className="input h-8 w-16 text-right tabular-nums" aria-label={t('scheme.value')} />
                      <span className="text-ink-muted text-[13px] w-3">{UNIT[r.type]}</span>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {msg && <p role="status" className={`mt-4 text-sm rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
      {!readOnly && (
        <button className="btn-primary mt-4" disabled={saving || sum !== 100 || !thOk} onClick={save}>
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('common.save')}
        </button>
      )}
    </section>
  )
}
