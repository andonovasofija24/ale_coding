import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'

/** A password field with an eye button that shows / hides what was typed. */
export default function PasswordInput(props: Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'>) {
  const { t } = useLanguage()
  const [shown, setShown] = useState(false)
  return (
    <div className="relative">
      <input {...props} type={shown ? 'text' : 'password'} className={`${props.className ?? 'input'} pr-11`} />
      <button type="button" onClick={() => setShown((s) => !s)}
        className="absolute right-1 top-1/2 -translate-y-1/2 w-9 h-9 rounded-md flex items-center justify-center text-ink-muted hover:text-ink hover:bg-paper"
        aria-label={shown ? t('auth.hidePassword') : t('auth.showPassword')} aria-pressed={shown} title={shown ? t('auth.hidePassword') : t('auth.showPassword')}>
        {shown ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </div>
  )
}
