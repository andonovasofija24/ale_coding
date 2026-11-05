import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import { adminApi, subjectsApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { SubjectSummary, TaskListItem } from '../../types'
import { Plus, Pencil, Trash2, ArrowLeft, FileCode2, Upload, CheckCircle2, Search, FolderOpen, ChevronRight, Shapes } from 'lucide-react'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import { useAuth } from '../../contexts/AuthContext'
import TaskChip from '../../components/TaskChip'
import SubjectIcon from '../../components/SubjectIcon'
import SubjectForm from '../../components/SubjectForm'
import EmptyState from '../../components/EmptyState'
import { LANG_ORDER, langClass, langInfo } from '../../lib/languages'

export default function AdminTaskListPage() {
  const { user } = useAuth()
  const { t, formatDate } = useLanguage()
  const qc = useQueryClient()
  const imported = (useLocation().state as { imported?: number } | null)?.imported

  const { data: tasks = [], isLoading } = useQuery<TaskListItem[]>({
    queryKey: ['admin-tasks'],
    queryFn: adminApi.listTasks,
  })

  const { data: subj } = useQuery<{ subjects: SubjectSummary[] }>({ queryKey: ['subjects'], queryFn: subjectsApi.list })
  const subjects = subj?.subjects ?? []
  const [params, setParams] = useSearchParams()
  const open = params.get('subject')                 // the subject whose tasks are shown ("none" = without one)
  const q = params.get('q') ?? ''
  const langFilter = params.get('lang') ?? ''
  const setParam = (k: string, v: string) => setParams((p) => { const n = new URLSearchParams(p); if (v) n.set(k, v); else n.delete(k); return n }, { replace: true })
  const [editing, setEditing] = useState<SubjectSummary | null | 'new'>(null)
  const matches = (x: TaskListItem) => (!q.trim() || x.title.toLowerCase().includes(q.trim().toLowerCase())) && (!langFilter || x.language === langFilter)
  const filtering = !!q.trim() || !!langFilter
  const known = new Set(subjects.map((s) => s.id))
  const langs = LANG_ORDER.filter((l) => tasks.some((x) => x.language === l))
  // one card per subject that has (matching) tasks, in the subjects' order; tasks without a subject last
  const cards = [...subjects.map((s) => ({ key: s.id, s, items: tasks.filter((x) => x.subject_id === s.id && matches(x)) })),
    { key: 'none', s: null as SubjectSummary | null, items: tasks.filter((x) => (!x.subject_id || !known.has(x.subject_id)) && matches(x)) }]
    .filter((g) => g.items.length > 0)
  const current = open ? cards.find((g) => g.key === open) ?? { key: open, s: subjects.find((s) => s.id === open) ?? null, items: [] } : null

  const deleteTask = useMutation({
    mutationFn: (id: string) => adminApi.deleteTask(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-tasks'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const handleDelete = async (id: string, title: string) => {
    // Say how much student work goes with the task before asking.
    let message = t('admin.deleteConfirm', { title })
    try {
      const usage = await adminApi.taskUsage(id)
      if (usage.sessions > 0) message += '\n\n' + t('admin.deleteUsage', { sessions: usage.sessions, students: usage.students })
    } catch { /* the plain confirmation is still correct */ }
    if (confirm(message)) deleteTask.mutate(id)
  }

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false}>
        {user?.role === 'admin' && <span className="hidden sm:inline ml-2 text-xs font-bold text-white bg-ink rounded px-2 py-1">{t('common.admin')}</span>}
      </AppHeader>
      <AdminNav />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <Link to="/courses" className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {t('admin.studentView')}
        </Link>

        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">{t('admin.manageTasks')}</h1>
            <p className="mt-1 text-ink-muted">{t('admin.intro', { n: tasks.length })}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {user?.role === 'admin' && <button className="btn-ghost" onClick={() => setEditing('new')}><Shapes size={15} /> {t('subjForm.new')}</button>}
            <Link to="/admin/tasks/import" className="btn-secondary">
              <Upload size={15} /> {t('import.button')}
            </Link>
            <Link to="/admin/tasks/new" className="btn-primary">
              <Plus size={16} /> {t('admin.newTask')}
            </Link>
          </div>
        </div>

        {!!imported && (
          <p role="status" className="mt-6 flex items-center gap-2 text-sm font-semibold text-ok bg-ok-soft rounded-lg px-4 py-3">
            <CheckCircle2 size={16} /> {t('import.done', { n: imported })}
          </p>
        )}

        <div className="mt-8">
          {isLoading ? (
            <div className="card divide-y divide-line-soft">
              {[1, 2, 3].map((i) => (
                <div key={i} className="px-5 py-4 animate-pulse"><div className="h-4 bg-paper rounded w-1/3" /></div>
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <div className="card px-6 py-14 text-center">
              <FileCode2 size={28} className="mx-auto text-ink-faint" />
              <p className="mt-3 font-semibold">{t('admin.noTasks')}</p>
              <p className="mt-1 text-sm text-ink-muted">{t('admin.noTasksHint')}</p>
              <Link to="/admin/tasks/new" className="btn-primary mt-5">
                <Plus size={16} /> {t('admin.newTask')}
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-5 flex flex-wrap items-center gap-2">
                <label className="relative flex-1 min-w-[12rem]">
                  <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <input className="input pl-9 h-9" value={q} onChange={(e) => setParam('q', e.target.value)} placeholder={t('bank.search')} aria-label={t('bank.search')} />
                </label>
                <select className="input h-9 w-auto" value={langFilter} onChange={(e) => setParam('lang', e.target.value)} aria-label={t('bank.language')}>
                  <option value="">{t('bank.allLanguages')}</option>
                  {langs.map((l) => <option key={l} value={l}>{langInfo(l).label}</option>)}
                </select>
                {filtering && <button className="btn-ghost btn-sm" onClick={() => setParams(open ? { subject: open } : {}, { replace: true })}>{t('bank.clear')}</button>}
              </div>

              {!current ? (
                <>
                  {filtering && <p className="mb-3 text-[13px] text-ink-muted">{t('bank.found', { n: cards.reduce((a, g) => a + g.items.length, 0), subjects: cards.length })}</p>}
                  {cards.length === 0 ? (
                    <EmptyState compact icon={<Search size={20} />} tone="ink" title={t('bank.nothing')} text={t('bank.nothingHint')} />
                  ) : (
                    <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {cards.map((g) => <li key={g.key}><BankCard g={g} /></li>)}
                    </ul>
                  )}
                </>
              ) : (
                <section aria-label={current.s?.name ?? t('bank.noSubject')}>
                  <button className="btn-ghost btn-sm -ml-2 mb-3" onClick={() => setParam('subject', '')}><ArrowLeft size={14} /> {t('bank.allSubjectsBack')}</button>
                  <div className="flex items-center gap-3 mb-3">
                    {current.s ? <SubjectIcon icon={current.s.icon} color={current.s.color} size={40} /> : <span className="w-10 h-10 rounded-xl bg-line flex items-center justify-center text-ink-muted"><FolderOpen size={19} /></span>}
                    <div className="min-w-0 flex-1">
                      <h2 className="font-extrabold text-xl leading-tight">{current.s ? current.s.name : t('bank.noSubject')}</h2>
                      <p className="text-[13px] text-ink-muted">{current.s && <span className="font-mono mr-1.5">{current.s.code}</span>}{t('bank.count', { n: current.items.length })}{filtering ? ' · ' + t('bank.filtered') : ''}</p>
                    </div>
                    {current.s && user?.role === 'admin' && <button className="btn-ghost btn-sm" onClick={() => setEditing(current.s)}><Pencil size={14} /> {t('subjForm.edit')}</button>}
                  </div>
                  {current.items.length === 0 ? <EmptyState compact icon={<FileCode2 size={20} />} tone="cobalt" title={t('bank.subjectEmpty')} /> : (
            <ul className="card divide-y divide-line-soft overflow-hidden" style={current.s ? { borderLeft: `4px solid ${current.s.color}` } : undefined}>
              {current.items.map((task) => (
                <li key={task.id} className="flex items-center gap-4 px-4 sm:px-5 py-3.5">
                  <div className="min-w-0 flex-1">
                    <Link to={`/admin/tasks/${task.id}/edit`} className="block font-semibold truncate hover:text-cobalt">
                      {task.title}
                    </Link>
                    <p className="mt-0.5 text-[13px] text-ink-muted">
                      <TaskChip kind={task.kind} lang={task.language} />
                      <span className="inline-block w-1 h-1 rounded-full bg-ink-faint mx-2 align-middle" />
                      {formatDate(task.created_at)}
                      {task.is_public === false && (
                        <span className="ml-2 text-[11px] font-semibold text-obj bg-obj-soft rounded-full px-2 py-0.5 align-middle">{t('form.courseOnly')}</span>
                      )}
                    </p>
                  </div>
                  <Link to={`/admin/tasks/${task.id}/edit`} className="btn-secondary btn-sm">
                    <Pencil size={14} /> <span className="hidden sm:inline">{t('admin.edit')}</span>
                  </Link>
                  <button
                    onClick={() => handleDelete(task.id, task.title)}
                    className="btn-danger btn-sm px-2"
                    disabled={deleteTask.isPending}
                    aria-label={t('admin.delete')}
                    title={t('admin.delete')}
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
                  )}
                </section>
              )}
            </>
          )}
          {deleteTask.isError && (
            <p role="alert" className="mt-3 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{t('admin.deleteFailed')}</p>
          )}
        </div>
      </main>
      {editing && <SubjectForm subject={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  )

  function BankCard({ g }: { g: { key: string; s: SubjectSummary | null; items: TaskListItem[] } }) {
    const inCard = LANG_ORDER.filter((l) => g.items.some((x) => x.language === l))
    return (
      <button onClick={() => setParam('subject', g.key)} className="group relative card p-4 h-full w-full text-left flex flex-col overflow-hidden border-2 hover:border-ink transition-colors">
        <span className="absolute inset-x-0 top-0 h-1.5" style={{ background: g.s?.color ?? '#CED4DA' }} aria-hidden />
        <span className="flex items-start gap-3 mt-1">
          {g.s ? <SubjectIcon icon={g.s.icon} color={g.s.color} /> : <span className="w-11 h-11 rounded-xl bg-line flex items-center justify-center text-ink-muted shrink-0"><FolderOpen size={20} /></span>}
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1.5 text-[11px] font-bold text-ink-muted">
              {g.s ? <><span className="font-mono text-ink">{g.s.code}</span>{g.s.semester && <> · {t('subj.semShort', { n: g.s.semester })}</>}
                {g.s.elective && <span className="ml-1 rounded-full bg-marker-soft text-marker-deep px-1.5 py-px">{t('subj.elective')}</span>}</> : t('bank.noSubjectHint')}
            </span>
            <span className="block mt-0.5 font-bold text-[15px] leading-snug group-hover:text-cobalt">{g.s ? g.s.name : t('bank.noSubject')}</span>
          </span>
        </span>
        <span className="mt-auto pt-3 flex items-end gap-2">
          <span className="flex flex-wrap gap-1 min-w-0 flex-1">
            {inCard.map((l) => <span key={l} className={`${langClass(l)} text-[10.5px] font-bold rounded px-1.5 py-0.5 bg-marker-soft text-marker-deep whitespace-nowrap`}>{langInfo(l).label}</span>)}
          </span>
          <span className="shrink-0 inline-flex items-center gap-1 text-[12px] font-bold text-ink-muted tabular-nums whitespace-nowrap">{t('bank.count', { n: g.items.length })} <ChevronRight size={14} /></span>
        </span>
      </button>
    )
  }
}
