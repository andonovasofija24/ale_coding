import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ssoApi } from '../services/api'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import AuthLayout from '../components/AuthLayout'
import PasswordInput from '../components/PasswordInput'

export default function LoginPage() {
  const { login } = useAuth()
  const { t, tError } = useLanguage()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [params] = useSearchParams()
  const ssoError = params.get('sso_error')
  const { data: sso } = useQuery({ queryKey: ['sso-config'], queryFn: ssoApi.config, staleTime: Infinity, retry: 0 })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/courses')
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'auth.loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <h2 className="text-2xl font-bold tracking-tight">{t('auth.loginTitle')}</h2>
      <p className="mt-1.5 text-sm text-ink-muted">{t('auth.loginSubtitle')}</p>

      {ssoError && (
        <p role="alert" className="mt-6 text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">
          {t(`sso.error.${['domain', 'cancelled', 'exists', 'disabled'].includes(ssoError) ? ssoError : 'generic'}` as any)}
        </p>
      )}

      {sso?.enabled && (
        <>
          <a href={ssoApi.loginUrl()} className="btn-secondary btn-lg w-full mt-8">
            <MicrosoftLogo /> {t('sso.button')}
          </a>
          <div className="mt-6 flex items-center gap-3 text-xs text-ink-faint">
            <span className="h-px flex-1 bg-line" /> {t('sso.or')} <span className="h-px flex-1 bg-line" />
          </div>
        </>
      )}

      <form onSubmit={handleSubmit} className={`${sso?.enabled ? 'mt-6' : 'mt-8'} space-y-4`}>
        <div>
          <label htmlFor="email" className="field-label">{t('auth.email')}</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            placeholder={t('auth.emailPlaceholder')}
            required
          />
        </div>
        <div>
          <label htmlFor="password" className="field-label">{t('auth.password')}</label>
          <PasswordInput
            id="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            required
          />
        </div>
        {error && (
          <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>
        )}
        <button type="submit" disabled={loading} className="btn-primary btn-lg w-full">
          {loading && <Loader2 size={16} className="animate-spin" />}
          {loading ? t('auth.signingIn') : t('auth.signIn')}
        </button>
      </form>

      <p className="mt-8 text-sm text-ink-muted">
        {t('auth.noAccount')}{' '}
        <Link to="/register" className="font-semibold text-cobalt hover:underline underline-offset-2">{t('auth.register')}</Link>
      </p>
    </AuthLayout>
  )
}

/** The four-square Microsoft logo (as Microsoft's sign-in button guidelines ask). */
function MicrosoftLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 21 21" aria-hidden>
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  )
}
