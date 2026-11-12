import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, KeyRound, Loader2, Search, UserPlus, Users } from 'lucide-react'
import { coursesApi, subjectsApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { Course, Permission, PermTemplate, SubjectSummary } from '../../types'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import EmptyState, { IconTile, SectionTitle } from '../../components/EmptyState'
import PermissionsEditor, { permLabel } from '../../components/PermissionsEditor'
import { TEMPLATES } from '../../lib/perms'

interface Teacher { user_id: string; name: string; email: string; permissions: Permission[]; template: PermTemplate | null }
interface Space extends Course { teachers: Teacher[] }

/** Admin: every subject has one space. Here: who teaches in which subject and what each of them may do there.
 *  Adding a teacher ticks a template's boxes; the exact permissions are changed one by one in the space. */
export default function AdminCoursesPage() {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const { data: spaces } = useQuery<Space[]>({ queryKey: ['admin-courses'], queryFn: coursesApi.adminList })
  const { data: subj } = useQuery<{ subjects: SubjectSummary[] }>({ queryKey: ['subjects'], queryFn: subjectsApi.list })
  const subjects = useMemo(() => new Map((subj?.subjects ?? []).map((s) => [s.id, s])), [subj])
  const [q, setQ] = useState('')
  const [onlyEmpty, setOnlyEmpty] = useState(false)
  const [open, setOpen] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [perms, setPerms] = useState<Permission[]>([...TEMPLATES.assistant])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const add = async (sp: Space) => {
    if (!email.trim()) return
    setBusy(true); setMsg(null)
    try {
      const r = await coursesApi.addMembers(sp.id, { emails: email.split(/[\s,;]+/).filter(Boolean), role: 'teacher', permissions: perms })
      setMsg(r.not_found.length ? { ok: false, text: `${t('course.notFoundEmails')} ${r.not_found.join(', ')}` } : { ok: true, text: t('adminSpaces.added') })
      setEmail('')
      qc.invalidateQueries({ queryKey: ['admin-courses'] })
    } catch (er: any) { setMsg({ ok: false, text: tError(er.response?.data?.detail, 'course.actionFailed') }) }
    finally { setBusy(false) }
  }

  const needle = q.trim().toLowerCase()
  const shown = (spaces ?? []).filter((c) => (!onlyEmpty || c.teachers.length === 0) && (!needle ||
    `${c.code} ${c.name} ${c.teachers.map((x) => `${x.name} ${x.email}`).join(' ')}`.toLowerCase().includes(needle)))
  // by semester, like the catalogue; electives without a semester and test subjects last
  const sem = (c: Space) => (c.subject_id && subjects.get(c.subject_id)?.semester) || 99
  shown.sort((a, b) => sem(a) - sem(b) || a.name.localeCompare(b.name))

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-start gap-4">
          <IconTile tone="ink" size="lg"><KeyRound size={26} /></IconTile>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">{t('adminSpaces.title')}</h1>
            <p className="mt-2 text-ink-muted max-w-2xl">{t('adminSpaces.intro')}</p>
          </div>
        </div>

        <section className="mt-8">
          <div className="flex flex-wrap items-center gap-3 mb-3">
            <SectionTitle icon={<Users size={15} />} tone="cobalt">{t('adminSpaces.all', { n: spaces?.length ?? 0 })}</SectionTitle>
            <label className="inline-flex items-center gap-2 text-[13px] text-ink-muted">
              <input type="checkbox" checked={onlyEmpty} onChange={(e) => setOnlyEmpty(e.target.checked)} /> {t('adminSpaces.onlyEmpty')}
            </label>
            <label className="relative ml-auto w-full sm:w-72">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input className="input pl-9 h-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('adminSpaces.search')} aria-label={t('adminSpaces.search')} />
            </label>
          </div>
          {!spaces ? <Loader2 className="animate-spin text-ink-muted" /> : shown.length === 0 ? (
            <EmptyState compact icon={<Users size={20} />} title={t('adminSpaces.none')} text={t('adminSpaces.noneHint')} />
          ) : (
            <ul className="card divide-y divide-line-soft">
              {shown.map((c) => {
                const s = c.subject_id ? subjects.get(c.subject_id) : undefined
                return (
                  <li key={c.id} className="px-4 sm:px-5 py-3.5">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                      <span className="font-mono text-[11px] font-bold bg-ink text-white rounded px-1.5 py-0.5">{s?.code ?? c.code}</span>
                      <Link to={`/courses/${c.id}`} className="font-bold hover:text-cobalt">{c.name}</Link>
                      <span className="text-[12px] text-ink-muted">
                        {s?.semester ? t('subj.semester', { n: s.semester }) : ''}{s?.elective ? ` · ${t('subj.elective').toLowerCase()}` : ''}
                        {' · '}{c.students === 1 ? t('courses.studentOne') : t('courses.studentsN', { n: c.students })}
                      </span>
                      <button type="button" className="ml-auto btn-ghost btn-sm" aria-expanded={open === c.id}
                        onClick={() => { setOpen(open === c.id ? null : c.id); setMsg(null) }}>
                        <UserPlus size={14} /> {t('adminSpaces.addTeacher')}
                      </button>
                      <Link to={`/courses/${c.id}?tab=students`} className="btn-ghost btn-sm">{t('adminSpaces.people')} <ArrowRight size={14} /></Link>
                    </div>
                    <ul className="mt-2 flex flex-wrap gap-1.5">
                      {c.teachers.length === 0 && <li className="text-[12.5px] text-ink-faint">{t('adminSpaces.noTeachers')}</li>}
                      {c.teachers.map((x) => (
                        <li key={x.user_id} className="inline-flex items-center gap-1.5 rounded-full border border-line-soft bg-white pl-2.5 pr-2 py-0.5 text-[12.5px]"
                          title={x.permissions.map((p) => t(`perm.${p}` as any)).join('\n')}>
                          <span className="font-medium">{x.name}</span>
                          <span className={`text-[11px] font-semibold rounded-full px-1.5 ${x.template === 'professor' ? 'bg-ink text-white' : x.template ? 'bg-cobalt-soft text-cobalt' : 'bg-marker-soft text-ink'}`}>
                            {permLabel(x.template, t, x.permissions)}
                          </span>
                        </li>
                      ))}
                    </ul>
                    {open === c.id && (
                      <form className="mt-3 rounded-xl border border-line-soft bg-paper p-4 space-y-3" onSubmit={(e) => { e.preventDefault(); add(c) }}>
                        <div className="flex flex-wrap gap-2">
                          <input className="input flex-1 min-w-[16rem]" value={email} onChange={(e) => setEmail(e.target.value)} type="text"
                            placeholder="ime.prezime@finki.ukim.mk" aria-label={t('adminSpaces.email')} autoFocus />
                          <button className="btn-primary" disabled={busy || !email.trim()}>{busy && <Loader2 size={15} className="animate-spin" />} {t('course.add')}</button>
                        </div>
                        <PermissionsEditor value={perms} onChange={setPerms} />
                        {msg && <p role="status" className={`text-[13px] ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
                      </form>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
