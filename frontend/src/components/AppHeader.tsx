import { ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, Settings2, GraduationCap, Library, Compass } from 'lucide-react'
import { useTour } from './Tour'
import { isStaff } from '../types'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import Avatar from './Avatar'
import Logo from './Logo'
import LanguageSwitcher from './LanguageSwitcher'

const ROLE_LABEL_KEYS = { student: 'role.student', teacher: 'role.teacher', assistant: 'role.teacher', professor: 'role.teacher', admin: 'role.admin' } as const

/** Top bar shared by the course, task list and admin pages: main sections + account. */
export default function AppHeader({ children, showAdminLink = true }: { children?: ReactNode; showAdminLink?: boolean }) {
  const { user, logout } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const tour = useTour()

  return (
    <header className="h-16 bg-surface border-b-2 border-ink relative z-10">
      <div className="h-full max-w-6xl mx-auto px-4 sm:px-6 flex items-center gap-4">
        <Link to="/courses" className="flex items-center gap-3 shrink-0" aria-label="ALE">
          <Logo />
        </Link>
        <nav className="flex items-center gap-0.5" aria-label={t('nav.main')}>
          <MainLink to="/courses" also="/subjects" tour="nav-courses" icon={<GraduationCap size={16} />} label={t('nav.courses')} />
          {isStaff(user) && <MainLink to="/admin/tasks" tour="nav-bank" icon={<Library size={16} />} label={t('nav.taskBank')} />}
        </nav>
        <div className="min-w-0 flex-1 flex items-center">{children}</div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button onClick={() => tour.start()} className="btn-ghost btn-sm px-2" data-tour="help" title={t('tour.helpHint')} aria-label={t('tour.help')}>
            <Compass size={16} /> <span className="hidden xl:inline">{t('tour.help')}</span>
          </button>
          <span data-tour="lang-switch"><LanguageSwitcher /></span>
          {showAdminLink && user?.role === 'admin' && (
            <Link to="/admin/monitoring" className="btn-ghost btn-sm hidden sm:inline-flex" data-tour="admin-link">
              <Settings2 size={15} /> {t('common.admin')}
            </Link>
          )}
          <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-line">
            <Link to="/profile" className="flex items-center gap-2 rounded-full pr-1 hover:bg-paper" title={t('profile.my')} data-tour="profile-link">
              <Avatar name={user?.name} url={user?.avatar_url} />
              <span className="hidden md:flex flex-col leading-tight max-w-[10rem]">
                <span className="text-sm font-medium text-ink-soft truncate">{user?.name}</span>
                {user && user.role !== 'student' && (
                  <span className="text-[11px] text-ink-muted">{t(ROLE_LABEL_KEYS[user.role])}</span>
                )}
              </span>
            </Link>
            <button
              onClick={() => { logout(); navigate('/login') }}
              className="btn-ghost btn-sm px-2"
              title={t('common.signOut')}
              aria-label={t('common.signOut')}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

function MainLink({ to, icon, label, also, tour }: { to: string; icon: ReactNode; label: string; also?: string; tour?: string }) {
  const here = useLocation().pathname
  return (
    <NavLink
      to={to}
      data-tour={tour}
      className={({ isActive: active }) => { const isActive = active || (!!also && here.startsWith(also)); return (
        `relative h-9 px-2.5 rounded-md inline-flex items-center gap-1.5 text-sm font-semibold transition-colors ${
          isActive ? 'bg-paper text-ink after:absolute after:left-1.5 after:right-1.5 after:-bottom-[15px] after:h-[4px] after:rounded-t after:bg-[#FCC419]'
            : 'text-ink-muted hover:text-ink hover:bg-paper/60'
        }`) }
      }
      title={label}
    >
      {icon} <span className="hidden lg:inline">{label}</span>
    </NavLink>
  )
}
