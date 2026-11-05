import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, Globe, GraduationCap, Hash, Loader2, Mail, MapPin, Pencil } from 'lucide-react'
import { profileApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Profile } from '../types'
import AppHeader from '../components/AppHeader'
import Avatar from '../components/Avatar'

/** Someone's profile, as I may see it (the server leaves out what I may not see). */
export default function UserProfilePage() {
  const { userId } = useParams<{ userId: string }>()
  const { t } = useLanguage()
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data: p, isLoading, isError } = useQuery<Profile>({ queryKey: ['user-profile', userId], queryFn: () => profileApi.of(userId!), retry: 0 })

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
          <ArrowLeft size={15} /> {t('profile.back')}
        </button>
        {isLoading ? <div className="flex justify-center py-20 text-ink-muted"><Loader2 className="animate-spin" /></div>
          : isError || !p ? <p className="py-20 text-center text-ink-muted">{t('profile.notFound')}</p> : (
          <article className="mt-4 card overflow-hidden">
            <div className="h-20 bg-[linear-gradient(120deg,#1A2233,#2747C9)]" aria-hidden />
            <div className="px-6 pb-6">
              <div className="-mt-12 flex items-end gap-4">
                <Avatar name={p.name} url={p.avatar_url} size={96} className="ring-4 ring-surface" />
                {user?.id === p.id && (
                  <Link to="/profile" className="ml-auto mb-1 btn-secondary btn-sm"><Pencil size={14} /> {t('profile.edit')}</Link>
                )}
              </div>
              <h1 className="mt-3 text-2xl font-extrabold tracking-tight">{p.name}</h1>
              <p className="text-sm text-ink-muted">{p.title || t(`role.${p.role}` as any)}</p>

              <dl className="mt-5 grid sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                {p.email && <Fact icon={<Mail size={15} />} label={t('auth.email')}><a href={`mailto:${p.email}`} className="text-cobalt hover:underline break-all">{p.email}</a></Fact>}
                {p.office && <Fact icon={<MapPin size={15} />} label={t('profile.office')}>{p.office}</Fact>}
                {p.consultation_hours && <Fact icon={<Clock size={15} />} label={t('profile.hours')}>{p.consultation_hours}</Fact>}
                {p.website && <Fact icon={<Globe size={15} />} label={t('profile.website')}><a href={p.website} target="_blank" rel="noopener noreferrer" className="text-cobalt hover:underline break-all">{p.website}</a></Fact>}
                {p.index_number && <Fact icon={<Hash size={15} />} label={t('profile.index')}><span className="font-mono">{p.index_number}</span></Fact>}
                {(p.study_program || p.study_year) && (
                  <Fact icon={<GraduationCap size={15} />} label={t('profile.program')}>
                    {[p.study_program, p.study_year ? t('profile.yearN', { n: p.study_year }) : ''].filter(Boolean).join(' · ')}
                  </Fact>
                )}
              </dl>
              {p.bio && <p className="mt-5 text-[15px] leading-relaxed whitespace-pre-wrap border-t border-line-soft pt-4">{p.bio}</p>}
            </div>
          </article>
        )}
      </main>
    </div>
  )
}

function Fact({ icon, label, children }: { icon: JSX.Element; label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2.5">
      <span className="mt-0.5 text-ink-muted">{icon}</span>
      <div className="min-w-0">
        <dt className="text-[12px] text-ink-muted">{label}</dt>
        <dd>{children}</dd>
      </div>
    </div>
  )
}
