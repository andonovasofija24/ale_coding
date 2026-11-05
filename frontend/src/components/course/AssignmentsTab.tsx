import { Link } from 'react-router-dom'
import { ChevronRight, Plus, Users } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { CourseDetail } from '../../types'
import { Deadline, KindBadge, StatusBadge, fmt } from './bits'

/** Staff: every assignment of the course (drafts too), with a link to create a new one. */
export default function AssignmentsTab({ course }: { course: CourseDetail }) {
  const { t } = useLanguage()
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-muted max-w-xl">{course.my_role === 'lab' ? t('course.assignmentsHintLab') : t('course.assignmentsHint')}</p>
        {<Link to={`/courses/${course.id}/assignments/new`} className="btn-primary" data-tour="assign-new"><Plus size={15} /> {t('assign.new')}</Link>}
      </div>
      {course.assignments.length === 0 ? (
        <div className="mt-6 card px-6 py-12 text-center text-ink-muted">{t('course.noAssignmentsStaff')}</div>
      ) : (
        <ul className="mt-5 card divide-y divide-line-soft overflow-hidden" data-tour="assignments-list">
          {course.assignments.map((a) => (
            <li key={a.id}>
              <Link to={`/assignments/${a.id}`} className="group flex items-center gap-4 px-4 sm:px-5 py-4 hover:bg-paper/60 transition-colors">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <KindBadge kind={a.kind} />
                    <StatusBadge status={a.status} />
                    {a.group_name && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-obj bg-obj-soft rounded-full px-2 py-0.5">
                        <Users size={11} /> {a.group_name}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 font-semibold group-hover:text-cobalt">{a.title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1">
                    <Deadline a={a} />
                    <span className="text-[13px] text-ink-muted">{(a.tasks.length === 1 ? t('assign.taskOne') : t('assign.tasksN', { n: a.tasks.length }))} · {fmt(a.max_points)} {t('assign.pointsShort')}</span>
                  </div>
                </div>
                <ChevronRight size={16} className="text-ink-faint group-hover:text-cobalt" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
