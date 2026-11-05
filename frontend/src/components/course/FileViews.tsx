import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Download, FileCode2, FileText, Folder, Loader2 } from 'lucide-react'
import { assignmentsApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { LineComment } from '../../types'
import CodeView from './CodeView'

export function formatSize(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

const TYPE_LABEL: Record<string, string> = {
  'application/pdf': 'PDF', 'image/png': 'PNG', 'image/jpeg': 'JPEG', 'application/zip': 'ZIP', 'text/plain': 'TXT',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
  'application/vnd.oasis.opendocument.text': 'ODT', 'application/vnd.oasis.opendocument.presentation': 'ODP',
  'application/vnd.oasis.opendocument.graphics': 'ODG',
}
export const typeLabel = (t: string) => TYPE_LABEL[t] ?? t

/** A handed-in file: PDFs and pictures are shown in the page, everything else can be downloaded. */
export function FilePreview({ submissionId, fileType, fileName, height = '36rem' }: {
  submissionId: string; fileType: string; fileName: string; height?: string
}) {
  const { t } = useLanguage()
  const inline = fileType === 'application/pdf' || fileType.startsWith('image/')
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (!inline) return
    let alive = true, made: string | null = null
    assignmentsApi.fileUrl(submissionId).then((u) => { made = u; if (alive) setUrl(u) }).catch(() => alive && setFailed(true))
    return () => { alive = false; if (made) URL.revokeObjectURL(made) }
  }, [submissionId, inline])

  return (
    <div className="rounded-lg border border-line bg-surface overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-line-soft text-sm">
        <FileText size={15} className="text-ink-muted" />
        <span className="min-w-0 flex-1 truncate font-medium">{fileName}</span>
        <span className="text-[11px] font-bold text-ink-muted">{typeLabel(fileType)}</span>
        <button type="button" onClick={() => assignmentsApi.download(submissionId, fileName)} className="btn-ghost btn-sm">
          <Download size={14} /> {t('files.download')}
        </button>
      </div>
      {!inline ? (
        <p className="px-4 py-8 text-center text-sm text-ink-muted">{t('files.noPreview')}</p>
      ) : failed ? (
        <p className="px-4 py-8 text-center text-sm text-bad">{t('files.previewFailed')}</p>
      ) : !url ? (
        <div className="py-12 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
      ) : fileType === 'application/pdf' ? (
        <iframe src={url} title={fileName} className="w-full bg-paper" style={{ height }} />
      ) : (
        <div className="bg-paper flex justify-center p-3"><img src={url} alt={fileName} className="max-w-full max-h-[36rem] object-contain" /></div>
      )}
    </div>
  )
}

/** A project zip: the file tree on the left, the chosen file on the right (read only; staff can comment on lines). */
export function ProjectBrowser({ submissionId, comments = [], onAdd, onDelete }: {
  submissionId: string; comments?: LineComment[]
  onAdd?: (path: string, line: number, body: string) => Promise<void>; onDelete?: (id: string) => Promise<void>
}) {
  const { t } = useLanguage()
  const { data: tree, isLoading } = useQuery<{ files: { path: string; size: number }[] }>({
    queryKey: ['zip-tree', submissionId], queryFn: () => assignmentsApi.tree(submissionId),
  })
  const files = useMemo(() => (tree?.files ?? []).slice().sort((a, b) => a.path.localeCompare(b.path)), [tree])
  const [path, setPath] = useState<string | null>(null)
  useEffect(() => {
    if (!path && files.length) {
      // open the first source file (README or main.* first)
      const pick = files.find((f) => /readme/i.test(f.path)) ?? files.find((f) => /main\./i.test(f.path)) ?? files.find((f) => f.size < 200_000) ?? files[0]
      setPath(pick.path)
    }
  }, [files, path])
  const { data: entry, isFetching } = useQuery<{ text: string | null; reason: string | null; size: number }>({
    queryKey: ['zip-entry', submissionId, path], queryFn: () => assignmentsApi.entry(submissionId, path!), enabled: !!path,
  })
  const counts = useMemo(() => {
    const m = new Map<string, number>()
    comments.forEach((c) => c.path && m.set(c.path, (m.get(c.path) ?? 0) + 1))
    return m
  }, [comments])

  if (isLoading) return <div className="py-10 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
  return (
    <div className="grid md:grid-cols-[15rem_minmax(0,1fr)] gap-3">
      <nav className="rounded-lg border border-line bg-surface max-h-[32rem] overflow-y-auto py-1" aria-label={t('files.projectFiles')}>
        <p className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-muted">{t('files.filesN', { n: files.length })}</p>
        {files.map((f) => {
          const depth = f.path.split('/').length - 1
          const dir = f.path.includes('/') ? f.path.slice(0, f.path.lastIndexOf('/') + 1) : ''
          return (
            <button key={f.path} type="button" onClick={() => setPath(f.path)} title={f.path}
              className={`w-full flex items-center gap-1.5 px-3 py-1 text-left text-[13px] ${path === f.path ? 'bg-marker-soft font-semibold' : 'hover:bg-paper'}`}>
              {depth > 0 && <Folder size={12} className="text-ink-faint shrink-0" />}
              <FileCode2 size={13} className="text-ink-muted shrink-0" />
              <span className="min-w-0 truncate"><span className="text-ink-faint">{dir}</span>{f.path.slice(dir.length)}</span>
              {counts.get(f.path) ? <span className="ml-auto text-[10px] font-bold text-cobalt bg-cobalt-soft rounded-full px-1.5">{counts.get(f.path)}</span> : null}
            </button>
          )
        })}
      </nav>
      <div className="min-w-0">
        {path && (
          <p className="mb-1.5 flex items-center gap-1 text-[12px] font-mono text-ink-muted truncate">
            {path.split('/').map((part, i, all) => (
              <span key={i} className="inline-flex items-center gap-1">{part}{i < all.length - 1 && <ChevronRight size={11} />}</span>
            ))}
          </p>
        )}
        {!entry || isFetching ? <div className="py-10 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
          : entry.text == null ? (
            <p className="rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm text-ink-muted">
              {entry.reason === 'too_large' ? t('files.tooLargeToShow', { size: formatSize(entry.size) }) : t('files.binary')}
            </p>
          ) : (
            <CodeView code={entry.text} maxHeight="32rem"
              comments={comments.filter((c) => c.path === path)}
              onAdd={onAdd ? (line, body) => onAdd(path!, line, body) : undefined} onDelete={onDelete} />
          )}
      </div>
    </div>
  )
}
