import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, ClipboardCheck, Download, FileText, FolderArchive, Loader2, UploadCloud } from 'lucide-react'
import { assignmentsApi, tasksApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { Assignment, Task, Upload } from '../types'
import AppHeader from '../components/AppHeader'
import Markdown from '../components/Markdown'
import { Deadline, Points, fmt } from '../components/course/bits'
import { ProjectBrowser, formatSize, typeLabel } from '../components/course/FileViews'
import { formatDateTime } from '../lib/time'

/** A document / project / on-site task of an assignment: the instructions and (for files) handing in. */
export default function WorkPage() {
  const { assignmentId, taskId } = useParams<{ assignmentId: string; taskId: string }>()
  const { t, tError, lang } = useLanguage()
  const qc = useQueryClient()
  const { data: a } = useQuery<Assignment>({ queryKey: ['assignment', assignmentId], queryFn: () => assignmentsApi.get(assignmentId!) })
  const { data: task } = useQuery<Task>({ queryKey: ['task', taskId], queryFn: () => tasksApi.get(taskId!) })
  const { data: uploads = [] } = useQuery<Upload[]>({
    queryKey: ['uploads', assignmentId, taskId], queryFn: () => assignmentsApi.myUploads(assignmentId!, taskId!),
  })
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)
  const [showFiles, setShowFiles] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  if (!a || !task) return <Shell><div className="flex justify-center py-20 text-ink-muted"><Loader2 className="animate-spin" /></div></Shell>
  const at = a.tasks.find((x) => x.task_id === taskId)
  const kind = task.kind ?? 'document'
  const staff = a.my_role !== 'student'
  const open = staff || (a.exam ? a.exam_state === 'running' : a.status === 'open' || a.status === 'late')
  const pointsHidden = !staff && a.scores_after_publish && !a.grades_published
  const latest = uploads[0]

  const send = async (file?: File) => {
    if (!file) return
    const max = kind === 'project' ? 50 : 20
    if (file.size > max * 1024 * 1024) { setError(t('files.tooBig', { n: max })); return }
    if (kind === 'project' && !/\.zip$/i.test(file.name)) { setError(t('err.Upload the project as a .zip file')); return }
    setError(''); setProgress(0)
    try {
      await assignmentsApi.upload(assignmentId!, taskId!, file, setProgress)
      qc.invalidateQueries({ queryKey: ['uploads', assignmentId, taskId] })
      qc.invalidateQueries({ queryKey: ['assignment', assignmentId] })
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'files.uploadFailed'))
    } finally {
      setProgress(null)
      if (input.current) input.current.value = ''
    }
  }

  const icon = kind === 'project' ? <FolderArchive size={14} /> : kind === 'offline' ? <ClipboardCheck size={14} /> : <FileText size={14} />
  return (
    <Shell>
      <Link to={`/assignments/${a.id}`} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
        <ArrowLeft size={15} /> {a.title}
      </Link>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-muted">{icon} {t(`kind.${kind}` as any)}</span>
        {at && <span className="ml-auto text-sm">{pointsHidden ? <span className="text-ink-muted">/ {fmt(at.points)}</span>
          : <Points got={at.my_score ?? null} max={at.points} />}</span>}
      </div>
      <h1 className="mt-1 text-3xl font-extrabold tracking-tight">{task.title}</h1>
      <div className="mt-2"><Deadline a={a} live /></div>

      <div className="mt-6 card p-5 sm:p-6 task-description"><Markdown>{task.description}</Markdown></div>

      {kind === 'offline' ? (
        <p className="mt-6 card px-5 py-4 text-sm text-ink-soft flex items-start gap-2">
          <ClipboardCheck size={16} className="shrink-0 mt-0.5 text-ink-muted" /> {t('work.offline')}
        </p>
      ) : (
        <>
          <h2 className="mt-8 panel-title">{t('work.handIn')}</h2>
          <p className="mt-1 text-[13px] text-ink-muted">{kind === 'project' ? t('work.projectHint') : t('work.documentHint')}</p>
          <label
            onDragOver={(e) => { e.preventDefault(); if (open) setDrag(true) }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); if (open) send(e.dataTransfer.files?.[0]) }}
            className={`mt-3 flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              !open ? 'border-line bg-paper/50 text-ink-faint cursor-not-allowed'
                : drag ? 'border-cobalt bg-cobalt-soft cursor-copy' : 'border-line bg-surface hover:border-cobalt cursor-pointer'}`}>
            {progress != null ? (
              <>
                <Loader2 className="animate-spin text-cobalt" />
                <span className="text-sm font-semibold">{t('files.uploading', { n: progress })}</span>
                <span className="h-1.5 w-48 rounded-full bg-line-soft overflow-hidden"><span className="block h-full bg-cobalt" style={{ width: `${progress}%` }} /></span>
              </>
            ) : (
              <>
                <UploadCloud size={26} className={open ? 'text-cobalt' : ''} />
                <span className="text-sm font-semibold">{open ? t('files.drop') : t('submit.closed')}</span>
                <span className="text-[12px] text-ink-muted">{kind === 'project' ? t('files.projectTypes') : t('files.documentTypes')}</span>
              </>
            )}
            <input ref={input} type="file" className="sr-only" disabled={!open || progress != null}
              accept={kind === 'project' ? '.zip,application/zip' : '.pdf,.png,.jpg,.jpeg,.docx,.pptx,.xlsx,.odt,.odp,.odg,.txt,.md,.drawio,.puml'}
              onChange={(e) => send(e.target.files?.[0])} />
          </label>
          {error && <p role="alert" className="mt-3 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}

          {uploads.length > 0 && (
            <>
              <h2 className="mt-8 panel-title">{t('files.myUploads')}</h2>
              <ul className="mt-3 card divide-y divide-line-soft">
                {uploads.map((u, i) => (
                  <li key={u.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    {i === 0 ? <CheckCircle2 size={17} className="text-ok shrink-0" /> : <FileText size={17} className="text-ink-faint shrink-0" />}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{u.file_name}</p>
                      <p className="text-[12px] text-ink-muted">
                        {typeLabel(u.file_type)} · {formatSize(u.file_size)} · {formatDateTime(u.submitted_at, lang)}
                        {u.late && <span className="text-bad font-semibold"> · {t('grades.late')}</span>}
                        {i === 0 && <span className="text-ok font-semibold"> · {t('files.graded')}</span>}
                      </p>
                    </div>
                    <button type="button" onClick={() => assignmentsApi.download(u.id, u.file_name)} className="btn-ghost btn-sm"><Download size={14} /> {t('files.download')}</button>
                  </li>
                ))}
              </ul>
              {kind === 'project' && latest && (
                <div className="mt-4">
                  <button type="button" onClick={() => setShowFiles((v) => !v)} className="btn-secondary btn-sm">{showFiles ? t('files.hideContents') : t('files.showContents')}</button>
                  {showFiles && <div className="mt-3"><ProjectBrowser submissionId={latest.id} /></div>}
                </div>
              )}
            </>
          )}
        </>
      )}
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-10">{children}</main>
    </div>
  )
}
