import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import AuthLayout from '../components/AuthLayout'
import PasswordInput from '../components/PasswordInput'

export default function RegisterPage() {
  const { register } = useAuth()
  const { t, tError } = useLanguage()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(email, password, name)
      navigate('/courses')
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'auth.registrationFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <h2 className="text-2xl font-bold tracking-tight">{t('auth.createAccountTitle')}</h2>
      <p className="mt-1.5 text-sm text-ink-muted">{t('auth.joinSubtitle')}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <div>
          <label htmlFor="name" className="field-label">{t('auth.fullName')}</label>
          <input
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            required
          />
        </div>
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
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            required
            minLength={6}
          />
          <p className="field-hint">{t('auth.passwordHint')}</p>
        </div>
        {error && (
          <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>
        )}
        <button type="submit" disabled={loading} className="btn-primary btn-lg w-full">
          {loading && <Loader2 size={16} className="animate-spin" />}
          {loading ? t('auth.creatingAccount') : t('auth.createAccount')}
        </button>
      </form>

      <p className="mt-8 text-sm text-ink-muted">
        {t('auth.haveAccount')}{' '}
        <Link to="/login" className="font-semibold text-cobalt hover:underline underline-offset-2">{t('auth.signIn')}</Link>
      </p>
    </AuthLayout>
  )
}
