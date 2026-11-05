import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Camera, ExternalLink, IdCard, KeyRound, Loader2, Save, Trash2 } from 'lucide-react'
import { IconTile, SectionTitle } from '../components/EmptyState'
import { profileApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Profile } from '../types'
import AppHeader from '../components/AppHeader'
import Avatar from '../components/Avatar'
import PasswordInput from '../components/PasswordInput'
import OwnAIKeyCard from '../components/OwnAIKeyCard'

/** Crop the middle square of a picture and shrink it to 256×256 JPEG in the browser (small upload, no EXIF). */
async function squareJpeg(file: File, size = 256): Promise<Blob> {
  const img = await createImageBitmap(file)
  const side = Math.min(img.width, img.height)
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  canvas.getContext('2d')!.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, size, size)
  return new Promise((ok, fail) => canvas.toBlob((b) => (b ? ok(b) : fail(new Error('encode'))), 'image/jpeg', 0.88))
}

/** My profile: picture, name, the facts that matter for my role, who may see my e-mail, password. */
export default function ProfilePage() {
  const { t, tError } = useLanguage()
  const { refreshUser } = useAuth()
  const qc = useQueryClient()
  const { data: p } = useQuery<Profile>({ queryKey: ['profile'], queryFn: profileApi.mine })
  const [form, setForm] = useState<Profile | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [picBusy, setPicBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  useEffect(() => { if (p) setForm(p) }, [p])

  if (!form) return <Shell><div className="flex justify-center py-20 text-ink-muted"><Loader2 className="animate-spin" /></div></Shell>
  const staff = form.role !== 'student'
  const set = (k: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setMsg('')
    try {
      const out = await profileApi.update({
        name: form.name, bio: form.bio, show_email: form.show_email, title: form.title ?? '', office: form.office ?? '',
        consultation_hours: form.consultation_hours ?? '', website: form.website ?? '', index_number: form.index_number ?? '',
        study_program: form.study_program ?? '', study_year: form.study_year ? Number(form.study_year) : null,
        email_reminders: form.email_reminders !== false,
      })
      qc.setQueryData(['profile'], out)
      await refreshUser()
      setMsg(t('course.saved'))
    } catch (err: any) {
      setMsg(tError(err.response?.data?.detail, 'course.actionFailed'))
    } finally { setSaving(false) }
  }

  const pickPicture = async (file?: File) => {
    if (!file) return
    setPicBusy(true); setMsg('')
    try {
      await profileApi.uploadAvatar(await squareJpeg(file))
      await refreshUser(); qc.invalidateQueries({ queryKey: ['profile'] })
    } catch (err: any) {
      setMsg(tError(err.response?.data?.detail, 'profile.pictureFailed'))
    } finally { setPicBusy(false); if (fileRef.current) fileRef.current.value = '' }
  }
  const removePicture = async () => {
    setPicBusy(true)
    try { await profileApi.removeAvatar(); await refreshUser(); qc.invalidateQueries({ queryKey: ['profile'] }) } finally { setPicBusy(false) }
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-center gap-5" data-tour="profile-avatar">
        <div className="relative">
          <Avatar name={form.name} url={p?.avatar_url} size={96} />
          {picBusy && <span className="absolute inset-0 rounded-full bg-surface/70 flex items-center justify-center"><Loader2 className="animate-spin" /></span>}
        </div>
        <div className="flex-1 min-w-[14rem]">
          <h1 className="text-3xl font-extrabold tracking-tight">{t('profile.my')}</h1>
          <p className="mt-1 text-sm text-ink-muted">{t(`role.${form.role}` as any)} · {form.email}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" id="pic"
              onChange={(e) => pickPicture(e.target.files?.[0])} />
            <label htmlFor="pic" className="btn-secondary btn-sm cursor-pointer"><Camera size={14} /> {p?.avatar_url ? t('profile.changePicture') : t('profile.addPicture')}</label>
            {p?.avatar_url && <button onClick={removePicture} className="btn-ghost btn-sm"><Trash2 size={14} /> {t('profile.removePicture')}</button>}
            <Link to={`/users/${form.id}`} className="btn-ghost btn-sm"><ExternalLink size={14} /> {t('profile.preview')}</Link>
          </div>
        </div>
      </div>

      <form onSubmit={save} className="mt-8 space-y-5">
        <section className="card p-5 sm:p-6 space-y-4" data-tour="profile-facts">
          <SectionTitle icon={<IdCard size={15} />} tone="cobalt" hint={staff ? t('profile.factsHintStaff') : t('profile.factsHint')}>{t('profile.facts')}</SectionTitle>
          <div>
            <label htmlFor="p-name" className="field-label">{t('profile.name')}</label>
            <input id="p-name" className="input" value={form.name} onChange={set('name')} required maxLength={255} />
          </div>
          {staff ? (
            <>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="p-title" className="field-label">{t('profile.title')}</label>
                  <input id="p-title" className="input" value={form.title ?? ''} onChange={set('title')} maxLength={120} placeholder={t('profile.titlePlaceholder')} />
                </div>
                <div>
                  <label htmlFor="p-office" className="field-label">{t('profile.office')}</label>
                  <input id="p-office" className="input" value={form.office ?? ''} onChange={set('office')} maxLength={120} placeholder={t('profile.officePlaceholder')} />
                </div>
              </div>
              <div>
                <label htmlFor="p-hours" className="field-label">{t('profile.hours')}</label>
                <input id="p-hours" className="input" value={form.consultation_hours ?? ''} onChange={set('consultation_hours')} maxLength={300} placeholder={t('profile.hoursPlaceholder')} />
              </div>
              <div>
                <label htmlFor="p-web" className="field-label">{t('profile.website')}</label>
                <input id="p-web" type="url" className="input" value={form.website ?? ''} onChange={set('website')} maxLength={300} placeholder="https://" />
              </div>
            </>
          ) : (
            <div className="grid sm:grid-cols-[10rem_minmax(0,1fr)_8rem] gap-3">
              <div>
                <label htmlFor="p-index" className="field-label">{t('profile.index')}</label>
                <input id="p-index" className="input" value={form.index_number ?? ''} onChange={set('index_number')} maxLength={30} placeholder="211234" />
              </div>
              <div>
                <label htmlFor="p-prog" className="field-label">{t('profile.program')}</label>
                <input id="p-prog" className="input" value={form.study_program ?? ''} onChange={set('study_program')} maxLength={200} placeholder={t('profile.programPlaceholder')} />
              </div>
              <div>
                <label htmlFor="p-year" className="field-label">{t('profile.year')}</label>
                <select id="p-year" className="input" value={form.study_year ?? ''} onChange={(e) => setForm({ ...form, study_year: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">—</option>
                  {[1, 2, 3, 4, 5, 6].map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
              </div>
              <p className="sm:col-span-3 field-hint -mt-1">{t('profile.studentFactsHint')}</p>
            </div>
          )}
          <div>
            <label htmlFor="p-bio" className="field-label">{staff ? t('profile.bioStaff') : t('profile.bioStudent')}</label>
            <textarea id="p-bio" rows={staff ? 5 : 3} className="input h-auto py-2" value={form.bio} onChange={set('bio')} maxLength={3000}
              placeholder={staff ? t('profile.bioStaffPlaceholder') : t('profile.bioStudentPlaceholder')} />
          </div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 mt-0.5 accent-cobalt" checked={!!form.show_email} onChange={(e) => setForm({ ...form, show_email: e.target.checked })} />
            <span>
              <span className="font-semibold text-sm">{t('profile.showEmail')}</span>
              <span className="block text-[13px] text-ink-muted">{t('profile.showEmailHint')}</span>
            </span>
          </label>
          {!staff && (
            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 mt-0.5 accent-cobalt" checked={form.email_reminders !== false}
                onChange={(e) => setForm({ ...form, email_reminders: e.target.checked })} />
              <span>
                <span className="font-semibold text-sm">{t('profile.reminders')}</span>
                <span className="block text-[13px] text-ink-muted">{t('profile.remindersHint')}</span>
              </span>
            </label>
          )}
          <div className="flex items-center gap-3">
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} {t('common.save')}
            </button>
            {msg && <p className="text-sm text-ink-muted" role="status">{msg}</p>}
          </div>
        </section>
      </form>

      <OwnAIKeyCard />

      {form.auth_provider === 'password' ? <PasswordCard /> : (
        <p className="mt-5 text-[13px] text-ink-muted">{t('profile.microsoftAccount')}</p>
      )}
    </Shell>
  )
}

function PasswordCard() {
  const { t, tError } = useLanguage()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setMsg(null)
    try {
      await profileApi.changePassword(current, next)
      setCurrent(''); setNext(''); setMsg({ ok: true, text: t('profile.passwordChanged') })
    } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'course.actionFailed') })
    } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="mt-5 card p-5 sm:p-6 space-y-4">
      <SectionTitle icon={<KeyRound size={15} />} tone="ink">{t('profile.password')}</SectionTitle>
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label htmlFor="pw-cur" className="field-label">{t('profile.currentPassword')}</label>
          <PasswordInput id="pw-cur" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} className="input" required />
        </div>
        <div>
          <label htmlFor="pw-new" className="field-label">{t('profile.newPassword')}</label>
          <PasswordInput id="pw-new" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} className="input" required minLength={8} />
          <p className="field-hint">{t('profile.newPasswordHint')}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy} className="btn-secondary">{busy && <Loader2 size={15} className="animate-spin" />} {t('profile.changePassword')}</button>
        {msg && <p className={`text-sm ${msg.ok ? 'text-ok' : 'text-bad'}`} role="status">{msg.text}</p>}
      </div>
    </form>
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
