import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, Copy, KeyRound, Link2, Loader2, Plus, School, Trash2, Wand2 } from 'lucide-react'
import { ltiApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatDateTime } from '../../lib/time'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import { IconTile, SectionTitle } from '../../components/EmptyState'
import EmptyState from '../../components/EmptyState'

interface Platform {
  id: string; name: string; issuer: string; client_id: string; deployment_ids: string[]; auth_login_url: string
  auth_token_url: string; jwks_url: string; link_by_email: boolean; active: boolean; users: number; courses: number
}
interface AdminLti {
  tool: { login: string; launch: string; jwks: string; deep_link: string; domain: string; public_jwk: object }
  platforms: Platform[]
  registrations: { url: string; name: string; expires_at: string }[]
}

function CopyField({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  const { t } = useLanguage()
  const [ok, setOk] = useState(false)
  return (
    <div className="grid sm:grid-cols-[13rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 py-2 border-b border-line-soft last:border-0">
      <span className="text-[13px] font-semibold text-ink-soft">{label}</span>
      <span className={`${mono ? 'font-mono text-[12.5px]' : 'text-sm'} break-all`}>{value}</span>
      <button type="button" className="btn-ghost btn-sm justify-self-start" aria-label={t('lti.copy')}
        onClick={() => { navigator.clipboard?.writeText(value); setOk(true); setTimeout(() => setOk(false), 1500) }}>
        {ok ? <Check size={14} className="text-ok" /> : <Copy size={14} />}
      </button>
    </div>
  )
}

/** Admin: ALE as an LTI 1.3 tool in the faculty's Moodle (courses.finki). */
export default function AdminLtiPage() {
  const { t, tError, lang } = useLanguage()
  const { data, refetch } = useQuery<AdminLti>({ queryKey: ['admin-lti'], queryFn: ltiApi.admin })
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [form, setForm] = useState({ name: 'courses.finki', issuer: '', client_id: '', deployment: '' })

  const run = async (k: string, fn: () => Promise<unknown>, ok?: string) => {
    setBusy(k); setMsg(null)
    try { await fn(); if (ok) setMsg({ ok: true, text: ok }); await refetch() } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'lti.failed') })
    } finally { setBusy('') }
  }
  const save = (p: Platform, change: Partial<Platform>) => run('p' + p.id, () => ltiApi.updatePlatform(p.id, { ...p, ...change }))

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-start gap-4">
          <IconTile tone="marker" size="lg"><School size={26} /></IconTile>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">{t('lti.admin.title')}</h1>
            <p className="mt-2 text-ink-muted max-w-2xl">{t('lti.admin.intro')}</p>
          </div>
        </div>
        {msg && <p role="status" className={`mt-6 text-sm font-semibold rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
        {!data ? <div className="flex justify-center py-16 text-ink-muted"><Loader2 className="animate-spin" /></div> : (
          <>
            {/* 1. the easy way: dynamic registration */}
            <section className="mt-8 card p-5 sm:p-6">
              <SectionTitle icon={<Wand2 size={15} />} tone="marker" hint={t('lti.admin.dynamicHint')}>{t('lti.admin.dynamic')}</SectionTitle>
              <ol className="mt-4 space-y-1.5 text-[14px] list-decimal pl-5 text-ink-soft">
                <li>{t('lti.admin.dyn1')}</li><li>{t('lti.admin.dyn2')}</li><li>{t('lti.admin.dyn3')}</li><li>{t('lti.admin.dyn4')}</li>
              </ol>
              <div className="mt-4">
                {data.registrations.map((r) => <CopyField key={r.url} label={t('lti.admin.regUntil', { when: formatDateTime(r.expires_at, lang) })} value={r.url} />)}
              </div>
              <button className="btn-primary mt-3" disabled={!!busy} onClick={() => run('reg', () => ltiApi.newRegistration(form.name), t('lti.admin.regMade'))}>
                {busy === 'reg' ? <Loader2 size={15} className="animate-spin" /> : <Link2 size={15} />} {t('lti.admin.newReg')}
              </button>
            </section>

            {/* 2. by hand */}
            <section className="mt-5 card p-5 sm:p-6">
              <SectionTitle icon={<KeyRound size={15} />} tone="cobalt" hint={t('lti.admin.manualHint')}>{t('lti.admin.manual')}</SectionTitle>
              <div className="mt-4">
                <CopyField label={t('lti.admin.toolUrl')} value={data.tool.launch} />
                <CopyField label={t('lti.admin.version')} value="LTI 1.3" mono={false} />
                <CopyField label={t('lti.admin.keyType')} value="Keyset URL" mono={false} />
                <CopyField label={t('lti.admin.keyset')} value={data.tool.jwks} />
                <CopyField label={t('lti.admin.loginUrl')} value={data.tool.login} />
                <CopyField label={t('lti.admin.redirect')} value={data.tool.launch} />
                <CopyField label={t('lti.admin.contentUrl')} value={data.tool.deep_link} />
              </div>
              <p className="mt-3 text-[13px] text-ink-muted">{t('lti.admin.services')}</p>
              <form className="mt-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end" onSubmit={(e) => {
                e.preventDefault()
                run('add', () => ltiApi.addPlatform({ name: form.name, issuer: form.issuer, client_id: form.client_id,
                  deployment_ids: form.deployment ? [form.deployment] : [] }), t('lti.admin.added'))
                  .then(() => setForm({ ...form, issuer: '', client_id: '', deployment: '' }))
              }}>
                <div><label className="field-label" htmlFor="lp-name">{t('lti.admin.name')}</label>
                  <input id="lp-name" className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div><label className="field-label" htmlFor="lp-iss">{t('lti.admin.issuer')}</label>
                  <input id="lp-iss" className="input font-mono text-[13px]" required placeholder="https://courses.finki.ukim.mk" value={form.issuer} onChange={(e) => setForm({ ...form, issuer: e.target.value })} /></div>
                <div><label className="field-label" htmlFor="lp-cid">{t('lti.admin.clientId')}</label>
                  <input id="lp-cid" className="input font-mono text-[13px]" required value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} /></div>
                <div><label className="field-label" htmlFor="lp-dep">{t('lti.admin.deployment')}</label>
                  <input id="lp-dep" className="input font-mono text-[13px]" value={form.deployment} onChange={(e) => setForm({ ...form, deployment: e.target.value })} /></div>
                <button className="btn-secondary sm:col-span-2 lg:col-span-4 justify-self-start" disabled={!!busy}>
                  {busy === 'add' ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />} {t('lti.admin.add')}
                </button>
              </form>
            </section>

            {/* 3. registered platforms */}
            <section className="mt-5">
              <SectionTitle icon={<School size={15} />} tone="ok">{t('lti.admin.platforms')}</SectionTitle>
              <div className="mt-3 space-y-3">
                {data.platforms.length === 0 && <EmptyState compact icon={<School size={20} />} tone="ok" title={t('lti.admin.noPlatforms')} text={t('lti.admin.noPlatformsHint')} />}
                {data.platforms.map((p) => (
                  <article key={p.id} className={`card p-4 sm:p-5 ${p.active ? '' : 'opacity-60'}`}>
                    <div className="flex flex-wrap items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-extrabold">{p.name} <span className="ml-2 text-[12px] font-semibold text-ink-muted">{t('lti.admin.counts', { users: p.users, courses: p.courses })}</span></p>
                        <p className="font-mono text-[12.5px] text-ink-soft break-all">{p.issuer}</p>
                        <p className="text-[12.5px] text-ink-muted mt-0.5">client_id <span className="font-mono">{p.client_id}</span> · deployment <span className="font-mono">{p.deployment_ids.join(', ') || t('lti.admin.anyDeployment')}</span></p>
                      </div>
                      <button className="btn-ghost btn-sm hover:text-bad" disabled={!!busy} onClick={() => {
                        if (confirm(t('lti.admin.deleteConfirm'))) run('d' + p.id, () => ltiApi.deletePlatform(p.id))
                      }}><Trash2 size={14} /> {t('lti.admin.delete')}</button>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[13.5px]">
                      <label className="flex items-center gap-2"><input type="checkbox" checked={p.active} onChange={(e) => save(p, { active: e.target.checked })} /> {t('lti.admin.active')}</label>
                      <label className="flex items-center gap-2"><input type="checkbox" checked={p.link_by_email} onChange={(e) => save(p, { link_by_email: e.target.checked })} /> {t('lti.admin.linkByEmail')}</label>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}
