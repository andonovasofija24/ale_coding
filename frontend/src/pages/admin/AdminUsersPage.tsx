import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Search } from 'lucide-react'
import { usersApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { useAuth } from '../../contexts/AuthContext'
import { AdminUser, UserRole } from '../../types'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'

const ROLES: UserRole[] = ['student', 'teacher', 'admin']

/** Admin: every account and its type (student / teacher / admin). What a teacher may do is ticked per subject. */
export default function AdminUsersPage() {
  const { t, tError, formatDate } = useLanguage()
  const { user: me } = useAuth()
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [role, setRole] = useState<string>('')
  const [error, setError] = useState('')
  const { data, isLoading } = useQuery<{ total: number; users: AdminUser[]; by_role: Record<string, number> }>({
    queryKey: ['admin-users', q, role], queryFn: () => usersApi.list({ q, role: role || undefined }), placeholderData: (p) => p,
  })

  const change = async (u: AdminUser, r: UserRole) => {
    setError('')
    try {
      await usersApi.setRole(u.id, r)
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'users.failed'))
    }
  }

  const counts = data?.by_role ?? {}
  const all = Object.values(counts).reduce((a, b) => a + b, 0)

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('users.title')}</h1>
        <p className="mt-2 text-ink-muted max-w-2xl">{t('users.intro')}</p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[14rem] max-w-sm">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
            <input className="input pl-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('users.search')} aria-label={t('users.search')} />
          </div>
          <div role="group" aria-label={t('users.role')} className="flex flex-wrap gap-1.5 text-[13px] font-semibold">
            {['', ...ROLES].map((r) => (
              <button key={r || 'all'} onClick={() => setRole(r)} aria-pressed={role === r}
                className={`h-8 px-3 rounded-full border transition-colors ${role === r ? 'bg-ink border-ink text-white' : 'bg-surface border-line text-ink-muted hover:text-ink'}`}>
                {r ? t(`role.${r}` as any) : t('tasks.filterAll')}
                <span className={`ml-1.5 tabular-nums ${role === r ? 'text-white/60' : 'text-ink-faint'}`}>{r ? counts[r] ?? 0 : all}</span>
              </button>
            ))}
          </div>
        </div>

        {error && <p role="alert" className="mt-4 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}

        <div className="mt-4 card overflow-x-auto">
          {isLoading && !data ? (
            <div className="flex justify-center py-10 text-ink-muted"><Loader2 className="animate-spin" /></div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[12px] text-ink-muted border-b border-line-soft">
                  <th className="px-4 py-2.5 font-semibold">{t('course.name')}</th>
                  <th className="px-4 py-2.5 font-semibold">{t('users.signIn')}</th>
                  <th className="px-4 py-2.5 font-semibold">{t('users.since')}</th>
                  <th className="px-4 py-2.5 font-semibold">{t('users.role')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {data?.users.map((u) => (
                  <tr key={u.id}>
                    <td className="px-4 py-2.5">
                      <p className="font-medium">{u.name}</p>
                      <p className="text-[12px] text-ink-muted">{u.email}</p>
                    </td>
                    <td className="px-4 py-2.5 text-[13px] text-ink-soft">{u.auth_provider === 'microsoft' ? 'Microsoft' : t('users.password')}</td>
                    <td className="px-4 py-2.5 text-[13px] text-ink-muted">{formatDate(u.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <select value={u.role} disabled={u.id === me?.id} onChange={(e) => change(u, e.target.value as UserRole)}
                        className="input h-8 w-auto text-[13px]" aria-label={t('users.role')}>
                        {ROLES.map((r) => <option key={r} value={r}>{t(`role.${r}` as any)}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
                {data && data.users.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-ink-muted">{t('users.none')}</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
        {data && data.total > data.users.length && (
          <p className="mt-2 text-[12px] text-ink-muted">{t('users.showing', { n: data.users.length, total: data.total })}</p>
        )}
        <dl className="mt-8 grid sm:grid-cols-2 gap-x-6 gap-y-2 text-[13px] text-ink-muted max-w-3xl">
          {ROLES.map((r) => (
            <div key={r}><dt className="inline font-semibold text-ink-soft">{t(`role.${r}` as any)}: </dt><dd className="inline">{t(`users.roleHelp.${r}` as any)}</dd></div>
          ))}
        </dl>
      </main>
    </div>
  )
}
