import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, Check, Eye, GraduationCap, Loader2 } from 'lucide-react'
import { assignmentsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { Assignment, Overview } from '../types'
import AppHeader from '../components/AppHeader'
import { fmt } from '../components/course/bits'

type Cell = 'saving' | 'saved' | 'error'
const ATT = ['present', 'absent', 'excused'] as const

/** Staff: points and attendance for the whole group in one table — like the sheet a lab assistant keeps, but
 *  straight into the gradebook. Tab moves right, Enter moves down; every cell is saved when you leave it. */
export default function QuickEntryPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const { t } = useLanguage()
  const qc = useQueryClient()
  const { data: a } = useQuery<Assignment>({ queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!) })
  const { data: ov, isLoading } = useQuery<Overview>({ queryKey: ['overview', assignmentId], queryFn: () => assignmentsApi.overview(assignmentId!) })
  const [group, setGroup] = useState('')
  const [state, setState] = useState<Record<string, Cell>>({})
  const [att, setAtt] = useState<Record<string, string | null>>({})

  const groups = useMemo(() => [...new Set((ov?.students ?? []).map((s) => s.group).filter(Boolean) as string[])].sort(), [ov])
  const students = (ov?.students ?? []).filter((s) => !group || s.group === group)
  const rubricTasks = new Set((a?.tasks ?? []).filter((x) => x.rubric).map((x) => x.task_id))

  const mark = (k: string, v: Cell) => setState((p) => ({ ...p, [k]: v }))
  const savePoints = async (userId: string, taskId: string, raw: string, before: number | null, max: number) => {
    const k = `${userId}:${taskId}`
    const v = raw.trim() === '' ? null : Number(raw.replace(',', '.'))
    if (v === before || (v == null && before == null)) return
    if (v != null && (isNaN(v) || v < 0 || v > max)) { mark(k, 'error'); return }
    mark(k, 'saving')
    try {
      await assignmentsApi.setGrade(assignmentId!, { user_id: userId, task_id: taskId, override: v } as any)
      mark(k, 'saved')
      qc.invalidateQueries({ queryKey: ['overview', assignmentId] })
      qc.invalidateQueries({ queryKey: ['gradebook'] })
    } catch { mark(k, 'error') }
  }
  const saveAtt = async (userId: string, status: string) => {
    const v = status || null
    setAtt((p) => ({ ...p, [userId]: v }))
    mark(`${userId}:att`, 'saving')
    try { await assignmentsApi.setAttendance(assignmentId!, userId, v); mark(`${userId}:att`, 'saved') } catch { mark(`${userId}:att`, 'error') }
  }
  // Enter: the same column, next student
  const down = (e: React.KeyboardEvent<HTMLInputElement>, row: number, col: number) => {
    if (e.key !== 'Enter') return
    e.preventDefault()
    ;(document.getElementById(`q-${row + 1}-${col}`) as HTMLInputElement | null)?.focus()
  }

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <Link to={`/assignments/${assignmentId}`} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {a?.title ?? t('common.loading')}
        </Link>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[16rem]">
            <h1 className="text-3xl font-extrabold tracking-tight">{t('quick.title')}</h1>
            <p className="mt-1 text-sm text-ink-muted max-w-2xl">{t('quick.hint')}</p>
          </div>
          {groups.length > 0 && (
            <select value={group} onChange={(e) => setGroup(e.target.value)} className="input h-9 w-auto" aria-label={t('course.group')}>
              <option value="">{t('course.allGroups')}</option>
              {groups.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          )}
          <Link to={`/assignments/${assignmentId}/grading`} className="btn-secondary"><GraduationCap size={15} /> {t('grading.open')}</Link>
        </div>

        {isLoading || !ov ? (
          <div className="flex justify-center py-16 text-ink-muted"><Loader2 className="animate-spin" /></div>
        ) : students.length === 0 ? (
          <div className="mt-6 card px-6 py-12 text-center text-ink-muted">{t('grades.noStudents')}</div>
        ) : (
          <div className="mt-5 card overflow-x-auto">
            <table className="text-sm border-separate border-spacing-0 w-full">
              <thead>
                <tr className="text-[12px] text-ink-muted">
                  <th className="sticky left-0 z-10 bg-surface text-left px-4 py-2.5 font-semibold border-b border-line-soft min-w-[12rem]">{t('course.name')}</th>
                  <th className="px-3 py-2.5 font-semibold border-b border-line-soft text-left">{t('quick.attendance')}</th>
                  {ov.tasks.map((x, i) => (
                    <th key={x.task_id} className="px-3 py-2.5 font-semibold border-b border-line-soft text-left min-w-[7.5rem]">
                      <span className="block truncate max-w-[10rem]" title={x.title}>{i + 1}. {x.title}</span>
                      <span className="block font-normal">/{fmt(x.points)} · {t(`kind.${x.kind}` as any)}</span>
                    </th>
                  ))}
                  <th className="px-4 py-2.5 font-semibold border-b border-line-soft text-right">{t('grades.total')}</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s, row) => (
                  <tr key={s.user_id} className="hover:bg-paper/50">
                    <td className="sticky left-0 z-10 bg-surface px-4 py-1.5 border-b border-line-soft">
                      <p className="font-medium truncate max-w-[14rem]">{s.name}</p>
                      <p className="text-[12px] text-ink-muted truncate max-w-[14rem]">{s.group ?? s.email}</p>
                    </td>
                    <td className="px-3 py-1.5 border-b border-line-soft">
                      <div className="flex items-center gap-1.5">
                        <select className="input h-8 w-auto text-[13px]" aria-label={t('quick.attendanceOf', { name: s.name })}
                          value={(att[s.user_id] !== undefined ? att[s.user_id] : s.attendance) ?? ''} onChange={(e) => saveAtt(s.user_id, e.target.value)}>
                          <option value="">—</option>
                          {ATT.map((v) => <option key={v} value={v}>{t(`att.${v}` as any)}</option>)}
                        </select>
                        <Status s={state[`${s.user_id}:att`]} />
                      </div>
                    </td>
                    {ov.tasks.map((x, col) => {
                      const c = s.tasks.find((y) => y.task_id === x.task_id)
                      const k = `${s.user_id}:${x.task_id}`
                      if (!c) return <td key={x.task_id} className="px-3 py-1.5 border-b border-line-soft text-ink-faint">·</td>
                      if (rubricTasks.has(x.task_id)) {
                        return (
                          <td key={x.task_id} className="px-3 py-1.5 border-b border-line-soft">
                            <Link to={`/assignments/${assignmentId}/grading?user=${s.user_id}&task=${x.task_id}`} className="inline-flex items-center gap-1 text-[13px] text-cobalt hover:underline tabular-nums">
                              {c.final == null ? '—' : fmt(c.final)} <Eye size={12} />
                            </Link>
                          </td>
                        )
                      }
                      return (
                        <td key={x.task_id} className="px-3 py-1.5 border-b border-line-soft">
                          <div className="flex items-center gap-1.5">
                            <input id={`q-${row}-${col}`} key={`${k}:${c.final}`} type="text" inputMode="decimal" defaultValue={c.final == null ? '' : String(c.final)}
                              placeholder={c.kind === 'code' && c.auto != null ? fmt(c.auto) : '—'}
                              aria-label={t('quick.pointsOf', { name: s.name, task: x.title })}
                              className={`input h-8 w-20 text-right tabular-nums ${state[k] === 'error' ? 'border-bad' : ''}`}
                              onKeyDown={(e) => down(e, row, col)}
                              onBlur={(e) => savePoints(s.user_id, x.task_id, e.target.value, c.final, x.points)} />
                            <Status s={state[k]} />
                          </div>
                        </td>
                      )
                    })}
                    <td className="px-4 py-1.5 border-b border-line-soft text-right font-bold tabular-nums">{s.total == null ? '—' : fmt(s.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-[12px] text-ink-muted">{t('quick.legend')}</p>
      </main>
    </div>
  )
}

function Status({ s }: { s?: Cell }) {
  const { t } = useLanguage()
  if (s === 'saving') return <Loader2 size={13} className="animate-spin text-ink-muted" />
  if (s === 'saved') return <Check size={14} className="text-ok" aria-label={t('course.saved')} />
  if (s === 'error') return <AlertCircle size={14} className="text-bad" aria-label={t('quick.invalid')} />
  return <span className="w-3.5" />
}
