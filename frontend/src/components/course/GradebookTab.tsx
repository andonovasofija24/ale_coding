import { useState } from 'react'
import { can } from '../../lib/perms'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { coursesApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { CourseDetail, Gradebook } from '../../types'
import { formatShortDate } from '../../lib/time'
import { fmt } from './bits'
import { ExcelButton, StandingTable } from './Standing'
import MoodleCard from './MoodleCard'
import GradingSchemeCard from './GradingSchemeCard'

/** Staff: students × assignments with each student's best points; CSV export for Excel / the faculty system. */
export default function GradebookTab({ course }: { course: CourseDetail }) {
  const { t, lang } = useLanguage()
  const { data, isLoading } = useQuery<Gradebook>({ queryKey: ['gradebook', course.id], queryFn: () => coursesApi.gradebook(course.id) })
  const [downloading, setDownloading] = useState(false)
  const [group, setGroup] = useState('')
  const [view, setView] = useState<'points' | 'standing'>('points')

  if (isLoading || !data) return <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>

  const students = data.students.filter((s) => !group || s.group === group)
  const maxTotal = data.assignments.reduce((n, a) => n + a.max_points, 0)

  return (
    <div>
      <div className="mb-5"><MoodleCard courseId={course.id} teacher={course.my_role === 'teacher'} hideWhenUnlinked /></div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg border border-line p-0.5" role="tablist" aria-label={t('course.tabGrades')}>
          {(['points', 'standing'] as const).map((v) => (
            <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)}
              className={`h-8 px-3 rounded-md text-[13px] font-semibold ${view === v ? 'bg-ink text-white' : 'text-ink-muted hover:text-ink'}`}>
              {t(v === 'points' ? 'grades.viewPoints' : 'grades.viewStanding')}
            </button>
          ))}
        </div>
        <p className="text-sm text-ink-muted flex-1 min-w-[16rem]">{view === 'points' ? t('grades.hint') : t('standing.hint')}</p>
        {course.groups.length > 0 && (
          <select value={group} onChange={(e) => setGroup(e.target.value)} className="input h-9 w-auto text-[13px]" aria-label={t('course.group')}>
            <option value="">{t('course.allGroups')}</option>
            {course.groups.map((g) => <option key={g.id} value={g.name}>{g.name}</option>)}
          </select>
        )}
        <ExcelButton course={course} group={group} />
        <button className="btn-secondary" disabled={downloading}
          onClick={async () => { setDownloading(true); try { await coursesApi.downloadGradebook(course.id) } finally { setDownloading(false) } }}>
          {downloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} {t('grades.csv')}
        </button>
      </div>

      {view === 'standing' ? <><StandingTable course={course} group={group} /><div className="mt-6"><GradingSchemeCard courseId={course.id} readOnly={!can(course, 'grades.rules')} /></div></> : data.students.length === 0 || data.assignments.length === 0 ? (
        <div className="mt-6 card px-6 py-12 text-center text-ink-muted">
          {data.assignments.length === 0 ? t('grades.noAssignments') : t('grades.noStudents')}
        </div>
      ) : (
        <div className="mt-4 card overflow-x-auto">
          <table className="text-sm border-separate border-spacing-0">
            <thead>
              <tr className="text-[12px] text-ink-muted">
                <th className="sticky left-0 z-10 bg-surface text-left px-4 py-2.5 font-semibold border-b border-line-soft min-w-[9rem] sm:min-w-[13rem]">{t('course.name')}</th>
                {data.assignments.map((a) => (
                  <th key={a.id} className="px-3 py-2.5 font-semibold border-b border-line-soft text-right align-bottom min-w-[7rem]">
                    <Link to={`/assignments/${a.id}/grading`} className={`block hover:text-cobalt ${a.published ? 'text-ink-soft' : 'text-ink-faint italic'}`}>{a.title}</Link>
                    <span className="block font-normal">
                      /{fmt(a.max_points)}{a.due_at ? ` · ${formatShortDate(a.due_at, lang)}` : ''}
                    </span>
                  </th>
                ))}
                <th className="px-4 py-2.5 font-semibold border-b border-line-soft text-right">{t('grades.total')}<span className="block font-normal">/{fmt(maxTotal)}</span></th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.user_id} className="hover:bg-paper/50">
                  <td className="sticky left-0 z-10 bg-surface px-4 py-2 border-b border-line-soft">
                    <p className="font-medium truncate max-w-[9rem] sm:max-w-[16rem]">{s.name}</p>
                    <p className="text-[12px] text-ink-muted truncate max-w-[9rem] sm:max-w-[16rem]">{s.group ? `${s.group} · ` : ''}{s.email}</p>
                  </td>
                  {data.assignments.map((a) => {
                    const c = s.scores[a.id]
                    return (
                      <td key={a.id} className={`px-3 py-2 border-b border-line-soft text-right tabular-nums ${c.applies ? '' : 'bg-paper/70'}`}>
                        {!c.applies ? <span className="text-ink-faint" title={t('grades.notForGroup')}>·</span>
                          : c.score == null ? <span className="text-ink-faint">—</span>
                          : (
                            <span className={c.score >= a.max_points ? 'text-ok font-semibold' : ''}>
                              {fmt(c.score)}{c.late && <sup className="ml-0.5 text-bad font-bold" title={t('grades.late')}>L</sup>}
                            </span>
                          )}
                      </td>
                    )
                  })}
                  <td className="px-4 py-2 border-b border-line-soft text-right font-bold tabular-nums">{fmt(s.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {view === 'points' && <p className="mt-3 text-[12px] text-ink-muted">{t('grades.legend')}</p>}
    </div>
  )
}
