import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, BellRing, CheckCircle2, Eye, Loader2, Mail, RefreshCw, Send } from 'lucide-react'
import { mailApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatDateTime } from '../../lib/time'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'

interface Delivery { address: string; lang: string; status: string; error: string; sent_at: string | null; course: string; kind: string; subject: string; body: string }
interface MailStatus { mode: 'preview' | 'smtp' | 'microsoft'; configured: boolean; missing: string; from: string; deliveries: Delivery[] }

/** Admin: how e-mail is sent (set in .env), a test message, the last messages — in preview mode this is the "inbox". */
export default function AdminMailPage() {
  const { t, tError, lang } = useLanguage()
  const { data, isFetching, refetch } = useQuery<MailStatus>({ queryKey: ['admin-mail'], queryFn: mailApi.adminStatus })
  const [to, setTo] = useState('')
  const [busy, setBusy] = useState<'' | 'test' | 'rem'>('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [open, setOpen] = useState<number | null>(null)

  const run = async (k: typeof busy, fn: () => Promise<string>) => {
    setBusy(k); setMsg(null)
    try { setMsg({ ok: true, text: await fn() }); refetch() } catch (err: any) {
      setMsg({ ok: false, text: tError(err.response?.data?.detail, 'mail.failed') })
    } finally { setBusy('') }
  }

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('adminMail.title')}</h1>
        <p className="mt-2 text-ink-muted max-w-2xl">{t('adminMail.intro')}</p>

        {!data ? <div className="flex justify-center py-16 text-ink-muted"><Loader2 className="animate-spin" /></div> : (
          <>
            <div className="mt-8 grid md:grid-cols-3 gap-4">
              <section className="card p-5 md:col-span-2">
                <p className="panel-title">{t('adminMail.mode')}</p>
                <p className="mt-1 text-2xl font-extrabold flex items-center gap-2">
                  {data.mode === 'preview' ? <Eye size={22} className="text-cobalt" /> : data.configured ? <CheckCircle2 size={22} className="text-ok" /> : <AlertTriangle size={22} className="text-bad" />}
                  {t(`adminMail.mode.${data.mode}` as any)}
                </p>
                <p className="mt-2 text-[13px] text-ink-muted">{t(`adminMail.modeHint.${data.mode}` as any)}</p>
                {!data.configured && <p className="mt-2 text-[13px] text-bad font-semibold">{t('adminMail.missing', { what: data.missing })}</p>}
                <p className="mt-3 text-[13px]"><span className="text-ink-muted">{t('adminMail.from')}:</span> <span className="font-mono">{data.from}</span></p>
                <pre className="mt-3 text-[12px] font-mono bg-paper rounded-lg p-3 overflow-x-auto text-ink-soft">{`MAIL_MODE=smtp          # or microsoft / preview
MAIL_FROM=ale@finki.ukim.mk
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=…  SMTP_PASSWORD=…`}</pre>
              </section>
              <section className="card p-5 space-y-4">
                <form onSubmit={(e) => { e.preventDefault(); run('test', async () => {
                  const r = await mailApi.adminTest(to)
                  return r.sent ? t('adminMail.testSent', { to }) : t('adminMail.testPreview')
                }) }}>
                  <label className="field-label" htmlFor="am-to">{t('adminMail.test')}</label>
                  <div className="flex gap-2">
                    <input id="am-to" type="email" required className="input" value={to} onChange={(e) => setTo(e.target.value)} placeholder="ime.prezime@finki.ukim.mk" />
                    <button className="btn-primary" disabled={!!busy} aria-label={t('adminMail.send')}>
                      {busy === 'test' ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                    </button>
                  </div>
                </form>
                <div>
                  <p className="field-label">{t('adminMail.reminders')}</p>
                  <button className="btn-secondary w-full" disabled={!!busy} onClick={() => run('rem', async () => t('adminMail.remindersDone', { n: (await mailApi.runReminders()).sent }))}>
                    {busy === 'rem' ? <Loader2 size={15} className="animate-spin" /> : <BellRing size={15} />} {t('adminMail.remindersRun')}
                  </button>
                  <p className="mt-1.5 text-[12px] text-ink-muted">{t('adminMail.remindersHint')}</p>
                </div>
                {msg && <p role="status" className={`text-sm rounded-lg px-3 py-2 ${msg.ok ? 'bg-ok-soft text-ok' : 'bg-bad-soft text-bad'}`}>{msg.text}</p>}
              </section>
            </div>

            <div className="mt-8 flex items-center gap-3">
              <h2 className="font-bold flex items-center gap-2 flex-1"><Mail size={17} /> {data.mode === 'preview' ? t('adminMail.inbox') : t('adminMail.last')}</h2>
              <button className="btn-ghost btn-sm" onClick={() => refetch()} disabled={isFetching}><RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} /> {t('adminMail.refresh')}</button>
            </div>
            {data.deliveries.length === 0 ? <div className="mt-3 card px-6 py-12 text-center text-ink-muted">{t('adminMail.none')}</div> : (
              <ul className="mt-3 card divide-y divide-line-soft overflow-hidden">
                {data.deliveries.map((d, i) => (
                  <li key={i}>
                    <button className="w-full text-left px-4 py-2.5 hover:bg-paper/60 grid sm:grid-cols-[12rem_minmax(0,1fr)_auto] gap-x-4 gap-y-0.5 items-center"
                      onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                      <span className="text-[13px] truncate">{d.address}</span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium truncate">{d.subject}</span>
                        <span className="block text-[12px] text-ink-muted">{d.course} · {t(`mailkind.${d.kind}` as any)} · {d.lang.toUpperCase()}{d.sent_at ? ` · ${formatDateTime(d.sent_at, lang)}` : ''}</span>
                      </span>
                      <span className={`text-[12px] font-semibold ${d.status === 'failed' ? 'text-bad' : d.status === 'sent' ? 'text-ok' : 'text-ink-muted'}`}>{t(`delivery.${d.status}` as any)}</span>
                    </button>
                    {open === i && (
                      <div className="px-4 pb-4">
                        {d.error && <p className="mb-2 text-[12px] text-bad break-words">{d.error}</p>}
                        <pre className="whitespace-pre-wrap break-words font-sans text-[13px] text-ink-soft bg-paper rounded-lg p-3">{d.body}</pre>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </main>
    </div>
  )
}
