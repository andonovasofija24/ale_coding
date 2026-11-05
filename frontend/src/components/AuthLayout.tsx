import { ReactNode } from 'react'
import { useLanguage } from '../i18n/LanguageContext'
import Logo from './Logo'
import LanguageSwitcher from './LanguageSwitcher'
import AccessCard from './AccessCard'
import CodeBackdrop from './CodeBackdrop'
import { LANG_ORDER, langInfo } from '../lib/languages'

/**
 * Split layout for login / register. The left side: what ALE is, and the access card the person gets once
 * signed in (still blank here).
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useLanguage()


  return (
    <div className="min-h-screen grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] bg-surface">
      {/* Brand / story panel */}
      <aside className="relative bg-ink text-white px-6 py-8 sm:px-10 lg:px-14 lg:py-12 flex flex-col overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />
        <CodeBackdrop columns={3} className="[mask-image:linear-gradient(to_bottom,black,black_15%,transparent_42%)] lg:[mask-image:linear-gradient(to_bottom,black,transparent_38%)]" />
        <div className="relative flex items-center justify-between">
          <Logo onDark />
          <LanguageSwitcher onDark className="lg:hidden" />
        </div>

        <div className="relative mt-10 lg:mt-auto max-w-md">
          <h1 className="text-3xl sm:text-4xl lg:text-[44px] font-extrabold leading-[1.08] tracking-tight">
            {t('auth.heroTitle')}
          </h1>
          <p className="mt-4 text-white/70 text-[15px] leading-relaxed max-w-sm">{t('auth.heroText')}</p>
          <p className="mt-5 font-mono text-[12px] text-white/45 leading-relaxed" aria-label={t('auth.languages')}>
            {LANG_ORDER.map((l) => langInfo(l).label).join(' · ')}
          </p>

          {/* the access card the person gets on sign-in, still blank */}
          <AccessCard blank className="mt-10 hidden sm:block max-w-[24rem] ring-1 ring-white/15 home-rise"
            name={t('auth.cardName')} role={t('auth.cardRole')} serial="№ ········" lines={[t('auth.cardLine')]} />
        </div>

        <p className="relative mt-10 lg:mt-12 text-xs text-white/40">{t('app.subtitle')}</p>
      </aside>

      {/* Form side */}
      <main className="relative flex items-center justify-center px-6 py-12 sm:px-10">
        <LanguageSwitcher className="absolute top-6 right-6 hidden lg:inline-flex" />
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  )
}
