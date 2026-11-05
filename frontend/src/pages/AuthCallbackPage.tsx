import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

/** Microsoft sign-in comes back here with the token in the URL fragment (#token=...). */
export default function AuthCallbackPage() {
  const { loginWithToken } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const done = useRef(false)

  useEffect(() => {
    if (done.current) return
    done.current = true
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
    history.replaceState(null, '', window.location.pathname) // don't leave the token in the address bar
    if (!token) {
      navigate('/login?sso_error=token', { replace: true })
      return
    }
    loginWithToken(token)
      .then(() => navigate('/courses', { replace: true }))
      .catch(() => navigate('/login?sso_error=token', { replace: true }))
  }, [loginWithToken, navigate])

  return (
    <div className="flex items-center justify-center gap-2 h-screen text-ink-muted">
      <Loader2 className="animate-spin" size={18} /> {t('sso.signingIn')}
    </div>
  )
}
