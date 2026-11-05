import { useEffect, useRef, useState } from 'react'
import { Eye, ImageUp, Loader2, Paperclip, X } from 'lucide-react'
import { tasksApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'

export interface DiagramUploadState {
  uploadId: string | null
  fileName: string | null
  reading: boolean
  error: string
  pick: () => void
  read: (file: File) => Promise<void>
  forget: () => void
  input: React.RefObject<HTMLInputElement>
}

const key = (taskId?: string) => `ale-diagram-upload:${taskId}`

/** "Upload a picture instead of drawing": the AI reads the student's own drawing into the editor; the picture is
 *  remembered (this tab) and handed in together with the diagram. */
export function useDiagramUpload(taskId: string | undefined, onDiagram: (json: string) => void): DiagramUploadState {
  const { tError } = useLanguage()
  const [saved, setSaved] = useState<{ id: string; name: string } | null>(() => {
    try { return JSON.parse(sessionStorage.getItem(key(taskId)) || 'null') } catch { return null }
  })
  const [reading, setReading] = useState(false)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)

  const read = async (file: File) => {
    setReading(true); setError('')
    try {
      const r = await tasksApi.readDiagram(taskId!, file)
      onDiagram(r.diagram)
      const s = { id: r.upload_id, name: r.file_name }
      setSaved(s)
      try { sessionStorage.setItem(key(taskId), JSON.stringify(s)) } catch { /* ignore */ }
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'dg.readFailed'))
    } finally {
      setReading(false)
      if (input.current) input.current.value = ''
    }
  }
  const forget = () => {
    setSaved(null)
    try { sessionStorage.removeItem(key(taskId)) } catch { /* ignore */ }
  }
  return { uploadId: saved?.id ?? null, fileName: saved?.name ?? null, reading, error, read, forget, input,
    pick: () => input.current?.click() }
}

export function DiagramUploadBar({ u, hasDiagram }: { u: DiagramUploadState; hasDiagram: boolean }) {
  const { t } = useLanguage()
  const [view, setView] = useState<string | null>(null)
  useEffect(() => () => { if (view) URL.revokeObjectURL(view) }, [view])
  return (
    <div className="border-b border-line-soft px-3 py-2 flex flex-wrap items-center gap-2 text-[12.5px] bg-paper/40 shrink-0">
      <input ref={u.input} type="file" accept=".png,.jpg,.jpeg,.pdf" className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f && (!hasDiagram || confirm(t('dg.replaceConfirm')))) u.read(f)
          else if (u.input.current) u.input.current.value = ''
        }} />
      <button className="btn-secondary btn-sm" onClick={u.pick} disabled={u.reading} title={t('dg.uploadHint')}>
        {u.reading ? <Loader2 size={14} className="animate-spin" /> : <ImageUp size={14} />} {u.reading ? t('dg.reading') : t('dg.upload')}
      </button>
      {u.fileName && !u.reading && (
        <span className="inline-flex items-center gap-1.5 text-ink-soft min-w-0">
          <Paperclip size={13} className="shrink-0" />
          <span className="truncate max-w-[14rem]">{t('dg.readFrom', { name: u.fileName })}</span>
          <button className="text-cobalt font-semibold hover:underline inline-flex items-center gap-1"
            onClick={async () => setView(await tasksApi.diagramUploadUrl(u.uploadId!))}><Eye size={13} /> {t('dg.viewPicture')}</button>
          <button className="text-ink-faint hover:text-bad" onClick={u.forget} title={t('dg.detach')} aria-label={t('dg.detach')}><X size={13} /></button>
        </span>
      )}
      {u.fileName && !u.reading && <span className="basis-full text-[11.5px] text-ink-muted">{t('dg.checkReading')}</span>}
      {u.error && <span role="alert" className="text-bad">{u.error}</span>}
      {view && (
        <div className="fixed inset-0 z-50 bg-ink/60 flex items-center justify-center p-4" role="dialog" aria-modal="true" onClick={() => setView(null)}>
          <div className="bg-surface rounded-xl shadow-modal max-w-5xl w-full h-[85vh] flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="h-11 px-4 flex items-center border-b border-line">
              <p className="font-semibold truncate flex-1">{u.fileName}</p>
              <button className="btn-ghost btn-sm" onClick={() => setView(null)} aria-label={t('mat.close')}><X size={16} /></button>
            </div>
            <iframe src={view} title={u.fileName ?? ''} className="flex-1 w-full border-0 bg-paper" />
          </div>
        </div>
      )}
    </div>
  )
}
