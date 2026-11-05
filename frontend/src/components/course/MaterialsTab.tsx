import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Download, Eye, EyeOff, FileText, Loader2, Pencil, Presentation, Trash2, Upload, X } from 'lucide-react'
import { materialsApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { CourseDetail, CourseMaterial } from '../../types'

type Section = CourseMaterial['section']
const SECTIONS: Section[] = ['lecture', 'exercise', 'other']

const kb = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)
const isSlides = (m: CourseMaterial) => /presentation|powerpoint/.test(m.file_type) || /\.(pptx?|odp)$/i.test(m.file_name)

/** Lectures, auditory exercises and other files. Staff upload and publish; students see what is published.
 *  Presentations and documents are shown as PDF in the page (converted on upload). */
export default function MaterialsTab({ course }: { course: CourseDetail }) {
  const { t } = useLanguage()
  const staff = course.my_role !== 'student'
  const { data, isLoading } = useQuery<{ can_convert: boolean; materials: CourseMaterial[] }>({
    queryKey: ['materials', course.id], queryFn: () => materialsApi.list(course.id),
  })
  const [viewing, setViewing] = useState<CourseMaterial | null>(null)

  if (isLoading || !data) return <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>

  const by = (s: Section) => data.materials.filter((m) => m.section === s)
  return (
    <div className="space-y-6">
      {staff && <UploadCard course={course} canConvert={data.can_convert} />}
      {data.materials.length === 0 ? (
        <div className="card px-6 py-12 text-center text-ink-muted">
          <BookOpen className="mx-auto mb-2 text-ink-faint" /> {staff ? t('mat.emptyStaff') : t('mat.empty')}
        </div>
      ) : SECTIONS.filter((s) => by(s).length).map((s) => (
        <section key={s}>
          <h2 className="panel-title mb-2">{t(`mat.section.${s}` as any)} <span className="text-ink-faint font-normal">· {by(s).length}</span></h2>
          <ul className="card divide-y divide-line-soft overflow-hidden">
            {by(s).map((m) => <Row key={m.id} m={m} staff={staff} courseId={course.id} onView={() => setViewing(m)} />)}
          </ul>
        </section>
      ))}
      {viewing && <Viewer m={viewing} onClose={() => setViewing(null)} />}
    </div>
  )
}

function Row({ m, staff, courseId, onView }: { m: CourseMaterial; staff: boolean; courseId: string; onView: () => void }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(m.title)
  const [week, setWeek] = useState<string>(m.week == null ? '' : String(m.week))
  const [err, setErr] = useState('')
  const act = async (fn: () => Promise<unknown>) => {
    setErr('')
    try { await fn(); qc.invalidateQueries({ queryKey: ['materials', courseId] }) } catch (e: any) { setErr(tError(e.response?.data?.detail, 'course.actionFailed')) }
  }
  const Icon = isSlides(m) ? Presentation : FileText
  return (
    <li className={`px-4 sm:px-5 py-3 flex flex-wrap sm:flex-nowrap items-center gap-3 ${!m.published ? 'bg-paper/60' : ''}`}>
      <span className="w-9 h-9 rounded-lg bg-cobalt-soft text-cobalt inline-flex items-center justify-center shrink-0"><Icon size={18} /></span>
      {editing ? (
        <form className="flex-1 min-w-0 flex flex-wrap gap-2" onSubmit={(e) => {
          e.preventDefault()
          act(() => materialsApi.update(m.id, { title: title.trim(), week: week === '' ? null : Number(week) })).then(() => setEditing(false))
        }}>
          <input className="input h-8 flex-1 min-w-[10rem]" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} required aria-label={t('mat.title')} />
          <input className="input h-8 w-20" type="number" min={0} max={30} value={week} onChange={(e) => setWeek(e.target.value)} placeholder={t('mat.week')} aria-label={t('mat.week')} />
          <button className="btn-primary btn-sm" type="submit">{t('common.save')}</button>
          <button className="btn-ghost btn-sm" type="button" onClick={() => setEditing(false)}>{t('mat.cancel')}</button>
        </form>
      ) : (
        <button onClick={m.has_preview ? onView : undefined} className={`flex-1 min-w-0 text-left ${m.has_preview ? 'group' : 'cursor-default'}`}>
          <span className="flex items-center gap-2">
            {m.week != null && <span className="text-[11px] font-bold text-ink-muted tabular-nums whitespace-nowrap">{t('mat.weekN', { n: m.week })}</span>}
            <span className="font-semibold truncate group-hover:text-cobalt">{m.title}</span>
            {!m.published && <span className="text-[11px] font-semibold rounded-full px-2 py-0.5 bg-line-soft text-ink-soft whitespace-nowrap">{t('mat.hidden')}</span>}
          </span>
          <span className="block text-[12px] text-ink-muted truncate">{m.file_name} · {kb(m.file_size)}</span>
          {err && <span className="block text-[12px] text-bad">{err}</span>}
        </button>
      )}
      {!editing && (
        <div className="flex items-center gap-1 ml-auto">
          {m.has_preview && (
            <button className="btn-secondary btn-sm" onClick={onView}><Eye size={14} /> {t('mat.open')}</button>
          )}
          <button className="btn-ghost btn-sm" onClick={() => materialsApi.download(m.id, m.file_name)} aria-label={t('mat.download')} title={t('mat.download')}>
            <Download size={15} />
          </button>
          {staff && (
            <>
              <button className="btn-ghost btn-sm" title={m.published ? t('mat.hide') : t('mat.publish')} aria-label={m.published ? t('mat.hide') : t('mat.publish')}
                onClick={() => act(() => materialsApi.update(m.id, { published: !m.published }))}>
                {m.published ? <EyeOff size={15} /> : <Eye size={15} className="text-cobalt" />}
              </button>
              <button className="btn-ghost btn-sm" onClick={() => setEditing(true)} aria-label={t('mat.edit')} title={t('mat.edit')}><Pencil size={14} /></button>
              <button className="btn-ghost btn-sm hover:text-bad" aria-label={t('mat.delete')} title={t('mat.delete')}
                onClick={() => confirm(t('mat.deleteConfirm', { name: m.title })) && act(() => materialsApi.remove(m.id))}>
                <Trash2 size={14} />
              </button>
            </>
          )}
        </div>
      )}
    </li>
  )
}

function UploadCard({ course, canConvert }: { course: CourseDetail; canConvert: boolean }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [f, setF] = useState({ title: '', section: 'lecture' as Section, week: '', published: true })
  const [pct, setPct] = useState<number | null>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const pick = (fl: File | null) => {
    setFile(fl); setMsg(null)
    if (fl && !f.title) setF((x) => ({ ...x, title: fl.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ') }))
  }
  const upload = async () => {
    if (!file) return
    setPct(0); setMsg(null)
    try {
      await materialsApi.upload(course.id, file, { title: f.title.trim(), section: f.section, week: f.week === '' ? null : Number(f.week), published: f.published }, setPct)
      qc.invalidateQueries({ queryKey: ['materials', course.id] })
      setFile(null); setF({ ...f, title: '', week: f.week === '' ? '' : String(Number(f.week) + 1) })
      if (input.current) input.current.value = ''
      setMsg({ ok: true, text: t('mat.uploaded') })
    } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'mat.uploadFailed') })
    } finally { setPct(null) }
  }

  return (
    <section className="card p-5">
      <h2 className="font-bold flex items-center gap-2"><Upload size={17} /> {t('mat.upload')}</h2>
      <p className="mt-1 text-[13px] text-ink-muted">{canConvert ? t('mat.uploadHint') : t('mat.uploadHintNoConvert')}</p>
      <div className="mt-3 grid sm:grid-cols-[minmax(0,1fr)_10rem_6rem] gap-3">
        <div className="sm:col-span-3">
          <label
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files?.[0] ?? null) }}
            className="flex items-center gap-3 rounded-lg border-2 border-dashed border-line hover:border-cobalt px-4 py-3 cursor-pointer">
            <Upload size={18} className="text-ink-muted shrink-0" />
            <span className="text-sm truncate">{file ? `${file.name} · ${kb(file.size)}` : t('mat.choose')}</span>
            <input ref={input} type="file" className="sr-only" accept=".pdf,.ppt,.pptx,.odp,.doc,.docx,.odt"
              onChange={(e) => pick(e.target.files?.[0] ?? null)} />
          </label>
        </div>
        <div>
          <label className="field-label" htmlFor="mt-title">{t('mat.title')}</label>
          <input id="mt-title" className="input" maxLength={300} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
        </div>
        <div>
          <label className="field-label" htmlFor="mt-sec">{t('mat.sectionLabel')}</label>
          <select id="mt-sec" className="input" value={f.section} onChange={(e) => setF({ ...f, section: e.target.value as Section })}>
            {SECTIONS.map((s) => <option key={s} value={s}>{t(`mat.section.${s}` as any)}</option>)}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="mt-week">{t('mat.week')}</label>
          <input id="mt-week" className="input" type="number" min={0} max={30} value={f.week} onChange={(e) => setF({ ...f, week: e.target.value })} />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" className="w-4 h-4 accent-cobalt" checked={f.published} onChange={(e) => setF({ ...f, published: e.target.checked })} />
          {t('mat.publishNow')}
        </label>
        <span className="flex-1" />
        <button className="btn-primary" disabled={!file || !f.title.trim() || pct !== null} onClick={upload}>
          {pct !== null ? <><Loader2 size={15} className="animate-spin" /> {pct < 100 ? `${pct}%` : t('mat.converting')}</> : <><Upload size={15} /> {t('mat.uploadBtn')}</>}
        </button>
      </div>
      {msg && <p role="status" className={`mt-3 text-sm rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
    </section>
  )
}

function Viewer({ m, onClose }: { m: CourseMaterial; onClose: () => void }) {
  const { t } = useLanguage()
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    let href: string | null = null
    materialsApi.viewUrl(m.id).then((u) => { href = u; setUrl(u) }).catch(() => setFailed(true))
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && close.current()
    window.addEventListener('keydown', esc)
    return () => { window.removeEventListener('keydown', esc); if (href) URL.revokeObjectURL(href) }
  }, [m.id])
  return (
    <div className="fixed inset-0 z-50 bg-ink/60 flex items-stretch sm:items-center justify-center sm:p-6" role="dialog" aria-modal="true" aria-label={m.title} onClick={onClose}>
      <div className="bg-surface sm:rounded-xl shadow-modal w-full max-w-6xl h-full sm:h-[90vh] flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-4 h-12 border-b border-line shrink-0">
          <p className="font-semibold truncate flex-1">{m.title}</p>
          <button className="btn-ghost btn-sm" onClick={() => materialsApi.download(m.id, m.file_name)}><Download size={15} /> <span className="hidden sm:inline">{t('mat.download')}</span></button>
          <button className="btn-ghost btn-sm" onClick={onClose} aria-label={t('mat.close')}><X size={16} /></button>
        </div>
        <div className="flex-1 bg-paper">
          {failed ? <p className="p-10 text-center text-ink-muted">{t('mat.noPreview')}</p>
            : url ? <iframe src={url} title={m.title} className="w-full h-full border-0" />
            : <div className="h-full flex items-center justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>}
        </div>
      </div>
    </div>
  )
}
