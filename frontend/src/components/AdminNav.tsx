import { NavLink } from 'react-router-dom'
import { FileCode2, Cpu, Activity, Users, Mail, School, GraduationCap, ArrowLeftRight } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { useAuth } from '../contexts/AuthContext'

/** Tabs of the staff/admin pages. Assistants and professors see the task bank; admins also see the rest. */
export default function AdminNav() {
  const { t } = useLanguage()
  const { user } = useAuth()
  const admin = user?.role === 'admin'
  const items = [
    { to: '/admin/tasks', label: t('adminNav.tasks'), icon: <FileCode2 size={15} />, end: false },
    ...(admin ? [
      { to: '/admin/courses', label: t('adminNav.courses'), icon: <GraduationCap size={15} />, end: true },
      { to: '/admin/electives', label: t('adminNav.electives'), icon: <ArrowLeftRight size={15} />, end: true },
      { to: '/admin/users', label: t('adminNav.users'), icon: <Users size={15} />, end: true },
      { to: '/admin/ai', label: t('adminNav.ai'), icon: <Cpu size={15} />, end: true },
      { to: '/admin/monitoring', label: t('adminNav.monitoring'), icon: <Activity size={15} />, end: true },
      { to: '/admin/mail', label: t('adminNav.mail'), icon: <Mail size={15} />, end: true },
      { to: '/admin/lti', label: t('adminNav.lti'), icon: <School size={15} />, end: true },
    ] : []),
  ]
  return (
    <nav className="bg-surface border-b border-line" aria-label={t('common.admin')}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex gap-1 overflow-x-auto">
        {items.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.end}
            className={({ isActive }) =>
              `h-11 px-3 flex items-center gap-1.5 text-sm font-semibold border-b-2 -mb-px whitespace-nowrap transition-colors ${
                isActive ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink'
              }`
            }
          >
            {it.icon} {it.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
