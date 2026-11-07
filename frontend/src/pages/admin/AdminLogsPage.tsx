import { useLanguage } from '../../i18n/LanguageContext'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import LogView from '../../components/LogView'

/** Admin: every AI call, test run and thing a person did — filter, follow live, export as CSV. */
export default function AdminLogsPage() {
  const { t } = useLanguage()
  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <AdminNav />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('log.title')}</h1>
        <p className="mt-1 mb-5 text-sm text-ink-muted max-w-3xl">{t('log.hintAdmin')}</p>
        <LogView mode="admin" />
      </main>
    </div>
  )
}
