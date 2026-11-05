import { Link } from 'react-router-dom'
import { Check, ChevronRight, Trash2 } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { SubjectTask } from '../types'
import LangChip from './LangChip'
import { langClass } from '../lib/languages'

/** A list of tasks to practise, each with my progress (new / step N / done). */
export default function TaskRows({ tasks, numbered = true, onDelete }: {
  tasks: SubjectTask[]; numbered?: boolean; onDelete?: (t: SubjectTask) => void
}) {
  const { t, formatDate } = useLanguage()
  return (
    <ol className="card divide-y divide-line-soft overflow-hidden">
      {tasks.map((task, i) => {
        const status = task.status
        return (
          <li key={task.id} className={`${langClass(task.language)} flex items-stretch`}>
            <Link to={`/tasks/${task.id}`} className="group flex-1 min-w-0 flex items-center gap-4 px-4 sm:px-5 py-3.5 hover:bg-paper/60 transition-colors">
              <span className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold border-b-2 ${
                status === 'completed' ? 'bg-ok text-white border-ok/60' : status === 'in_progress' ? 'bg-marker text-ink border-marker-deep/30' : 'bg-marker-soft text-marker-deep border-marker/40'}`}>
                {status === 'completed' ? <Check size={16} strokeWidth={3} /> : numbered ? i + 1 : <span className="w-2 h-2 rounded-full bg-marker" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold text-[15px] text-ink truncate group-hover:text-cobalt transition-colors">{task.title}</span>
                <span className="mt-0.5 flex items-center gap-2 text-[12.5px] text-ink-muted">
                  <LangChip lang={task.language} />
                  <span className="w-1 h-1 rounded-full bg-ink-faint" />
                  {formatDate(task.created_at)}
                </span>
              </span>
              <span className="hidden sm:block text-right text-[13px] shrink-0">
                {status === 'completed' ? <span className="font-semibold text-ok">{t('tasks.statusDone')}</span>
                  : status === 'in_progress' ? <span className="font-semibold text-ink">{t('tasks.statusInProgress', { n: (task.current_step ?? 0) + 1 })}</span>
                  : <span className="text-ink-muted">{t('tasks.statusNew')}</span>}
              </span>
              <ChevronRight size={18} className="shrink-0 text-ink-faint group-hover:text-cobalt transition-colors" />
            </Link>
            {onDelete && (
              <button onClick={() => onDelete(task)} className="px-3 text-ink-faint hover:text-bad hover:bg-bad-soft border-l border-line-soft"
                title={t('subj.deletePractice')} aria-label={t('subj.deletePractice')}><Trash2 size={15} /></button>
            )}
          </li>
        )
      })}
    </ol>
  )
}
