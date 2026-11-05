import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Check, ChevronRight, BookOpen } from 'lucide-react'
import { tasksApi, sessionsApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { TaskListItem, SessionSummary } from '../types'
import AppHeader from '../components/AppHeader'
import LangChip from '../components/LangChip'
import { LANG_ORDER, langClass, langInfo } from '../lib/languages'

export default function TaskListPage() {
  const { user } = useAuth()
  const { t, formatDate } = useLanguage()

  const { data: tasks = [], isLoading } = useQuery<TaskListItem[]>({
    queryKey: ['tasks'],
    queryFn: tasksApi.list,
  })
  const { data: mine = [] } = useQuery<SessionSummary[]>({
    queryKey: ['my-sessions'],
    queryFn: sessionsApi.mine,
  })

  const [filter, setFilter] = useState<string>('all')
  const langs = LANG_ORDER.filter((l) => tasks.some((x) => x.language === l))
  const shown = filter === 'all' ? tasks : tasks.filter((x) => x.language === filter)

  const progress = new Map(mine.map((s) => [s.task_id, s]))
  const doneCount = mine.filter((s) => s.status === 'completed').length
  const firstName = user?.name?.split(' ')[0] ?? ''

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <h1 className="text-3xl sm:text-[34px] font-extrabold tracking-tight leading-tight">
          {t('tasks.greeting', { name: firstName })}
        </h1>
        <p className="mt-2 text-ink-muted max-w-xl">{t('tasks.intro')}</p>

        {tasks.length > 0 && (
          <div className="mt-8 space-y-3">
            {/* Progress: one segment per task; segments shrink so any number of tasks fits in one line */}
            <div className="flex items-center gap-3 text-sm text-ink-muted">
              <div className="flex-1 min-w-0 flex gap-[3px]" aria-hidden>
                {tasks.map((task) => {
                  const st = progress.get(task.id)?.status
                  return (
                    <span
                      key={task.id}
                      className={`${langClass(task.language)} h-1.5 flex-1 min-w-[2px] max-w-6 rounded-full ${
                        st === 'completed' ? 'bg-ok' : st === 'in_progress' ? 'bg-marker' : 'bg-line'
                      }`}
                    />
                  )
                })}
              </div>
              <span className="shrink-0 whitespace-nowrap">{t('tasks.progress', { done: doneCount, total: tasks.length })}</span>
            </div>

            {langs.length > 1 && (
              <div role="group" aria-label={t('tasks.filterLabel')} className="flex flex-wrap gap-1.5 text-[13px] font-semibold">
                {['all', ...langs].map((l) => {
                  const active = filter === l
                  const count = l === 'all' ? tasks.length : tasks.filter((x) => x.language === l).length
                  return (
                    <button
                      key={l}
                      onClick={() => setFilter(l)}
                      aria-pressed={active}
                      className={`${l === 'all' ? '' : langClass(l)} h-7 px-2.5 rounded-full border flex items-center gap-1.5 transition-colors ${
                        active ? 'bg-ink border-ink text-white' : 'bg-surface border-line text-ink-muted hover:text-ink hover:border-ink-faint'
                      }`}
                    >
                      {l !== 'all' && <span className="w-2 h-2 rounded-full bg-marker" aria-hidden />}
                      {l === 'all' ? t('tasks.filterAll') : langInfo(l).label}
                      <span className={`tabular-nums ${active ? 'text-white/60' : 'text-ink-faint'}`}>{count}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        <section className="mt-4">
          {isLoading ? (
            <div className="card divide-y divide-line-soft">
              {[1, 2, 3].map((i) => (
                <div key={i} className="px-5 py-5 flex gap-4 animate-pulse">
                  <div className="w-8 h-8 rounded-lg bg-paper" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-paper rounded w-1/3" />
                    <div className="h-3 bg-paper rounded w-1/5" />
                  </div>
                </div>
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <div className="card px-6 py-14 text-center">
              <BookOpen size={28} className="mx-auto text-ink-faint" />
              <p className="mt-3 font-semibold">{t('tasks.empty')}</p>
              <p className="mt-1 text-sm text-ink-muted">{t('tasks.emptyHint')}</p>
            </div>
          ) : (
            <ol className="card divide-y divide-line-soft overflow-hidden">
              {shown.map((task) => {
                const i = tasks.indexOf(task)
                const p = progress.get(task.id)
                const status = p?.status
                return (
                  <li key={task.id} className={langClass(task.language)}>
                    <Link
                      to={`/tasks/${task.id}`}
                      className="group flex items-center gap-4 px-4 sm:px-5 py-4 hover:bg-paper/60 transition-colors"
                    >
                      <span
                        className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold ${
                          status === 'completed'
                            ? 'bg-ok text-white'
                            : status === 'in_progress'
                              ? 'bg-marker text-ink'
                              : 'bg-paper text-ink-muted'
                        }`}
                      >
                        {status === 'completed' ? <Check size={16} strokeWidth={3} /> : i + 1}
                      </span>

                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold text-[15.5px] text-ink truncate group-hover:text-cobalt transition-colors">
                          {task.title}
                        </span>
                        <span className="mt-0.5 flex items-center gap-2 text-[13px] text-ink-muted">
                          <LangChip lang={task.language} />
                          <span className="w-1 h-1 rounded-full bg-ink-faint" />
                          {formatDate(task.created_at)}
                        </span>
                      </span>

                      <span className="hidden sm:block text-right text-[13px] shrink-0">
                        {status === 'completed' ? (
                          <span className="font-semibold text-ok">{t('tasks.statusDone')}</span>
                        ) : status === 'in_progress' ? (
                          <span className="font-semibold text-ink">
                            {t('tasks.statusInProgress', { n: (p?.current_step ?? 0) + 1 })}
                          </span>
                        ) : (
                          <span className="text-ink-muted">{t('tasks.statusNew')}</span>
                        )}
                      </span>
                      <ChevronRight size={18} className="shrink-0 text-ink-faint group-hover:text-cobalt transition-colors" />
                    </Link>
                  </li>
                )
              })}
            </ol>
          )}
        </section>
      </main>
    </div>
  )
}
