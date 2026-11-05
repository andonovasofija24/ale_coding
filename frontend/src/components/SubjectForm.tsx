import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Loader2, Save, Trash2, X } from 'lucide-react'
import { subjectsApi } from '../services/api'
import { useLanguage } from '../i18n/LanguageContext'
import { Subject } from '../types'
import { LANG_ORDER, langInfo } from '../lib/languages'
import SubjectIcon, { SUBJECT_ICONS } from './SubjectIcon'

const COLORS = ['#2747C9', '#7048E8', '#0CA678', '#F08C00', '#D6336C', '#2B8A3E', '#1971C2', '#C2255C', '#0B7285', '#E8590C', '#495057', '#FF6B6B']

/** Admin: add or change a subject — code, names, semester, elective (also listed in its semester), languages, look. */
export default function SubjectForm({ subject, onClose }: { subject: Subject | null; onClose: () => void }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [f, setF] = useState({
    code: subject?.code ?? '', name: subject?.name_mk ?? '', name_en: subject?.name_en ?? '',
    semester: subject?.semester ? String(subject.semester) : '', elective: subject?.elective ?? false,
    languages: subject?.languages ?? [], icon: subject?.icon ?? 'book-open', color: subject?.color ?? '#2747C9',
    description: subject?.description ?? '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const done = () => { qc.invalidateQueries({ queryKey: ['subjects'] }); qc.invalidateQueries({ queryKey: ['admin-tasks'] }); onClose() }
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    const data = { ...f, semester: f.semester ? Number(f.semester) : null, elective: f.elective || !f.semester }
    try { if (subject) await subjectsApi.update(subject.id, data); else await subjectsApi.create(data); done() } catch (er: any) {
      setErr(tError(er.response?.data?.detail, 'subjForm.failed')); setBusy(false)
    }
  }
  const remove = async () => {
    if (!subject || !confirm(t('subjForm.deleteConfirm', { name: subject.name }))) return
    setBusy(true)
    try { await subjectsApi.remove(subject.id); done() } catch (er: any) { setErr(tError(er.response?.data?.detail, 'subjForm.failed')); setBusy(false) }
  }
  const toggleLang = (l: string) => setF({ ...f, languages: f.languages.includes(l) ? f.languages.filter((x) => x !== l) : [...f.languages, l] })

  return (
    <div className="fixed inset-0 z-50 bg-ink/50 flex items-start sm:items-center justify-center p-4 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="sf-title">
      <form onSubmit={save} className="card-stamp w-full max-w-2xl p-5 sm:p-6 space-y-4 my-8">
        <div className="flex items-center gap-3">
          <SubjectIcon icon={f.icon} color={f.color} size={40} />
          <h2 id="sf-title" className="text-xl font-extrabold flex-1">{subject ? t('subjForm.edit') : t('subjForm.new')}</h2>
          <button type="button" className="btn-ghost btn-sm px-1.5" onClick={onClose} aria-label={t('form.cancel')}><X size={16} /></button>
        </div>
        <div className="grid sm:grid-cols-[8rem_minmax(0,1fr)] gap-3">
          <div><label className="field-label" htmlFor="sf-code">{t('subjForm.code')}</label>
            <input id="sf-code" className="input font-mono" required maxLength={20} value={f.code} onChange={(e) => setF({ ...f, code: e.target.value.toUpperCase() })} placeholder="OOAID" /></div>
          <div><label className="field-label" htmlFor="sf-name">{t('subjForm.name')}</label>
            <input id="sf-name" className="input" required maxLength={200} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
        </div>
        <div><label className="field-label" htmlFor="sf-en">{t('subjForm.nameEn')}</label>
          <input id="sf-en" className="input" maxLength={200} value={f.name_en} onChange={(e) => setF({ ...f, name_en: e.target.value })} /></div>
        <div className="grid sm:grid-cols-2 gap-3 items-end">
          <div><label className="field-label" htmlFor="sf-sem">{t('subjForm.semester')}</label>
            <select id="sf-sem" className="input" value={f.semester} onChange={(e) => setF({ ...f, semester: e.target.value })}>
              <option value="">{t('subjForm.anySemester')}</option>
              {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => <option key={n} value={n}>{t('subj.semShort', { n })}</option>)}
            </select></div>
          <label className="flex items-start gap-2 text-sm pb-2">
            <input type="checkbox" className="mt-0.5" checked={f.elective || !f.semester} disabled={!f.semester}
              onChange={(e) => setF({ ...f, elective: e.target.checked })} />
            <span><span className="font-semibold">{t('subjForm.elective')}</span>
              <span className="block text-[12.5px] text-ink-muted">{f.semester ? t('subjForm.electiveHint', { n: f.semester }) : t('subjForm.electiveAny')}</span></span>
          </label>
        </div>
        <fieldset>
          <legend className="field-label">{t('subjForm.languages')}</legend>
          <div className="flex flex-wrap gap-1.5">
            {LANG_ORDER.map((l) => (
              <button type="button" key={l} onClick={() => toggleLang(l)} aria-pressed={f.languages.includes(l)}
                className={`h-7 px-2.5 rounded-full border text-[12.5px] font-semibold ${f.languages.includes(l) ? 'bg-ink text-white border-ink' : 'bg-surface border-line text-ink-muted hover:text-ink'}`}>
                {langInfo(l).label}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="grid sm:grid-cols-2 gap-3">
          <fieldset><legend className="field-label">{t('subjForm.icon')}</legend>
            <div className="flex flex-wrap gap-1.5">
              {SUBJECT_ICONS.map((i) => (
                <button type="button" key={i} onClick={() => setF({ ...f, icon: i })} aria-label={i} aria-pressed={f.icon === i}
                  className={`rounded-xl p-0.5 ${f.icon === i ? 'ring-2 ring-ink' : ''}`}><SubjectIcon icon={i} color={f.color} size={30} /></button>
              ))}
            </div></fieldset>
          <fieldset><legend className="field-label">{t('subjForm.color')}</legend>
            <div className="flex flex-wrap gap-1.5">
              {COLORS.map((c) => (
                <button type="button" key={c} onClick={() => setF({ ...f, color: c })} aria-label={c} aria-pressed={f.color === c}
                  className={`w-8 h-8 rounded-lg border-2 ${f.color === c ? 'border-ink' : 'border-transparent'}`} style={{ background: c }} />
              ))}
            </div></fieldset>
        </div>
        {err && <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{err}</p>}
        <div className="flex flex-wrap gap-2 pt-1">
          <button className="btn-primary" disabled={busy}>{busy ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('subjForm.save')}</button>
          <button type="button" className="btn-ghost" onClick={onClose}>{t('form.cancel')}</button>
          {subject && <button type="button" className="btn-ghost sm:ml-auto hover:text-bad" disabled={busy} onClick={remove}><Trash2 size={14} /> {t('subjForm.delete')}</button>}
        </div>
      </form>
    </div>
  )
}
