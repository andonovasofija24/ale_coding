import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, Check, Inbox, Loader2, X } from 'lucide-react'
import { electivesApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { ElectiveRequest } from '../../types'
import { formatDateTime } from '../../lib/time'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import EmptyState from '../../components/EmptyState'

type Filter = 'pending' | 'approved' | 'rejected' | 'all'

/**
 * Admin: students' requests to change an elective after they confirmed their choice — always one out and one in.
 * Approving makes the change; rejecting keeps the plan (the student sees the note either way).
 */
export default function AdminElectivesPage() {
  const { t, lang } = useLanguage()
  const [filter, setFilter] = useState<Filter>('pending')
  const { data, isLoading } = useQuery<{ requests: ElectiveRequest[]; pending: number }>({
    queryKey: ['elective-requests', filter], queryFn: () => electivesApi.adminList(filter),
  })
  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <AdminNav />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('el.adminTitle')}</h1>
        <p className="mt-1 text-sm text-ink-muted max-w-2xl">{t('el.adminHint')}</p>
        <div className="mt-5 flex flex-wrap gap-1.5" role="group" aria-label={t('el.adminTitle')}>
          {(['pending', 'approved', 'rejected', 'all'] as Filter[]).map((f) => (
            <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
              className={`h-8 px-3 rounded-full text-[13px] font-semibold border-[1.5px] ${filter === f ? 'bg-ink text-white border-ink' : 'bg-surface border-line-strong text-ink-soft hover:border-ink'}`}>
              {t(`el.status.${f}` as any)}{f === 'pending' && data ? <span className="opacity-60 tabular-nums"> {data.pending}</span> : null}
            </button>
          ))}
        </div>
        {isLoading || !data ? <div className="mt-10 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
          : data.requests.length === 0 ? (
            <div className="mt-6"><EmptyState icon={<Inbox size={24} />} tone="cobalt" title={t('el.noRequests')} text={t('el.noRequestsHint')} /></div>
          ) : (
            <ul className="mt-5 space-y-3">
              {data.requests.map((r) => <RequestCard key={r.id} r={r} lang={lang} />)}
            </ul>
          )}
      </main>
    </div>
  )
}

function RequestCard({ r, lang }: { r: ElectiveRequest; lang: string }) {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<'' | 'approve' | 'reject'>('')
  const [err, setErr] = useState('')
  const act = async (kind: 'approve' | 'reject') => {
    setBusy(kind); setErr('')
    try {
      await (kind === 'approve' ? electivesApi.approve(r.id, note) : electivesApi.reject(r.id, note))
      qc.invalidateQueries({ queryKey: ['elective-requests'] })
    } catch (e: any) { setErr(tError(e.response?.data?.detail, 'subjForm.failed')) } finally { setBusy('') }
  }

  const pending = r.status === 'pending'
  return (
    <li className={`card p-4 sm:p-5 border-2 ${pending ? 'border-ink' : ''}`}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="font-bold">{r.student?.name}</p>
        <p className="text-[12.5px] text-ink-muted">{r.student?.email}</p>
        <p className="ml-auto text-[12px] text-ink-muted">{formatDateTime(r.created_at, lang as any)}</p>
      </div>
      <div className="mt-3 grid sm:grid-cols-[1fr_auto_1fr] gap-2 items-center">
        {r.remove && !r.move ? (
          <div className="rounded-lg bg-bad-soft/60 px-3 py-2">
            <p className="text-[11.5px] font-bold text-bad">{t('el.out')}</p>
            <p className="font-semibold text-[14px]">{r.remove.name}</p>
            <p className="text-[12px] text-ink-muted font-mono">{r.remove.code} · {t('subj.semShort', { n: r.remove.semester })}</p>
          </div>
        ) : r.move && r.remove ? (
          <div className="rounded-lg bg-paper px-3 py-2">
            <p className="text-[11.5px] font-bold text-ink-muted">{t('el.nowIn')}</p>
            <p className="font-semibold text-[14px]">{r.remove.name}</p>
            <p className="text-[12px] text-ink-muted font-mono">{r.remove.code} · {t('subj.semShort', { n: r.remove.semester })}</p>
          </div>
        ) : <div className="rounded-lg border border-dashed border-line px-3 py-2 text-[12.5px] text-ink-muted">{t('el.nothingOut')}</div>}
        <ArrowLeftRight size={16} className="hidden sm:block text-ink-faint" aria-hidden />
        {r.add ? (
          <div className="rounded-lg bg-ok-soft/60 px-3 py-2">
            <p className="text-[11.5px] font-bold text-ok">{r.move ? t('el.moveTo') : t('el.in')}</p>
            <p className="font-semibold text-[14px]">{r.add.name}</p>
            <p className="text-[12px] text-ink-muted font-mono">{r.add.code} · {t('subj.semShort', { n: r.add.semester })}</p>
          </div>
        ) : <div className="rounded-lg border border-dashed border-line px-3 py-2 text-[12.5px] text-ink-muted">{t('el.nothingIn')}</div>}
      </div>
      {r.reason && <p className="mt-3 text-[13px] border-l-2 border-marker pl-2"><span className="text-ink-muted">{t('el.reason')}:</span> {r.reason}</p>}
      {pending ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input className="input h-9 flex-1 min-w-[12rem] text-[13px]" value={note} onChange={(e) => setNote(e.target.value)}
            placeholder={t('el.notePh')} aria-label={t('el.notePh')} maxLength={1000} />
          <button className="btn-secondary h-9" disabled={!!busy} onClick={() => act('reject')}>
            {busy === 'reject' ? <Loader2 size={15} className="animate-spin" /> : <X size={15} />} {t('el.reject')}
          </button>
          <button className="btn-primary h-9" disabled={!!busy} onClick={() => act('approve')}>
            {busy === 'approve' ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />} {t('el.approve')}
          </button>
        </div>
      ) : (
        <p className={`mt-3 text-[13px] font-semibold ${r.status === 'approved' ? 'text-ok' : r.status === 'rejected' ? 'text-bad' : 'text-ink-muted'}`}>
          {t(`el.status.${r.status}` as any)}{r.decided_at ? ` · ${formatDateTime(r.decided_at, lang as any)}` : ''}{r.admin_note ? ` — „${r.admin_note}“` : ''}
        </p>
      )}
      {err && <p role="alert" className="mt-2 text-[13px] text-bad">{err}</p>}
    </li>
  )
}
