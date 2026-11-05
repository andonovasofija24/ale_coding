import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, GraduationCap, Loader2, Plus, Search, Trash2, Users } from 'lucide-react'
import { coursesApi, subjectsApi } from '../../services/api'
import { useLanguage } from '../../i18n/LanguageContext'
import { Course, SubjectSummary } from '../../types'
import AppHeader from '../../components/AppHeader'
import AdminNav from '../../components/AdminNav'
import EmptyState, { IconTile, SectionTitle } from '../../components/EmptyState'

interface AdminCourse extends Course { teachers: string[]; assistants: string[]; labs: string[] }

/** Admin: every course; make a course for a subject, then put the people in it (Students tab of the course). */
export default function AdminCoursesPage() {
  const { t, tError } = useLanguage()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: courses } = useQuery<AdminCourse[]>({ queryKey: ['admin-courses'], queryFn: coursesApi.adminList })
  const { data: subj } = useQuery<{ subjects: SubjectSummary[] }>({ queryKey: ['subjects'], queryFn: subjectsApi.list })
  const subjects = subj?.subjects ?? []
  const [form, setForm] = useState({ subject_id: '', code: '', name: '', semester: '' })
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const pickSubject = (id: string) => {
    const s = subjects.find((x) => x.id === id)
    setForm({ ...form, subject_id: id, code: s ? (s.finki_code || s.code) : form.code, name: s ? s.name_mk : form.name })
  }
  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const c: Course = await coursesApi.create({ ...form, subject_id: form.subject_id || null })
      qc.invalidateQueries({ queryKey: ['admin-courses'] }); qc.invalidateQueries({ queryKey: ['courses'] })
      navigate(`/courses/${c.id}?tab=students`)
    } catch (er: any) { setErr(tError(er.response?.data?.detail, 'courses.createFailed')); setBusy(false) }
  }
  const remove = async (c: AdminCourse) => {
    if (!confirm(t('adminCourses.deleteConfirm', { name: c.name }))) return
    try { await coursesApi.remove(c.id); qc.invalidateQueries({ queryKey: ['admin-courses'] }); qc.invalidateQueries({ queryKey: ['courses'] }) }
    catch (er: any) { setErr(tError(er.response?.data?.detail, 'course.actionFailed')) }
  }
  const shown = (courses ?? []).filter((c) => !q.trim() || `${c.code} ${c.name} ${c.teachers.join(' ')}`.toLowerCase().includes(q.trim().toLowerCase()))
  const bySem = [1, 2, 3, 4, 5, 6, 7, 8].map((n) => ({ n, items: subjects.filter((s) => s.semester === n) })).filter((g) => g.items.length)

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader showAdminLink={false} />
      <AdminNav />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-start gap-4">
          <IconTile tone="ink" size="lg"><GraduationCap size={26} /></IconTile>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">{t('adminCourses.title')}</h1>
            <p className="mt-2 text-ink-muted max-w-2xl">{t('adminCourses.intro')}</p>
          </div>
        </div>

        <form onSubmit={create} className="mt-8 card p-5 sm:p-6 space-y-4">
          <SectionTitle icon={<Plus size={15} />} tone="ok" hint={t('adminCourses.newHint')}>{t('adminCourses.new')}</SectionTitle>
          <div className="grid md:grid-cols-[minmax(0,1.4fr)_9rem_minmax(0,1fr)_11rem] gap-3">
            <div><label className="field-label" htmlFor="ac-subj">{t('subj.ofCourse')}</label>
              <select id="ac-subj" className="input" value={form.subject_id} onChange={(e) => pickSubject(e.target.value)}>
                <option value="">{t('subj.none')}</option>
                {bySem.map((g) => (
                  <optgroup key={g.n} label={t('subj.semester', { n: g.n })}>
                    {g.items.map((s) => <option key={s.id} value={s.id}>{s.name}{s.elective ? ` (${t('subj.elective').toLowerCase()})` : ''}</option>)}
                  </optgroup>
                ))}
              </select></div>
            <div><label className="field-label" htmlFor="ac-code">{t('courses.code')}</label>
              <input id="ac-code" className="input font-mono" required maxLength={50} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></div>
            <div><label className="field-label" htmlFor="ac-name">{t('courses.name')}</label>
              <input id="ac-name" className="input" required maxLength={300} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><label className="field-label" htmlFor="ac-sem">{t('courses.semester')}</label>
              <input id="ac-sem" className="input" maxLength={100} value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })} placeholder={t('courses.semesterPlaceholder')} /></div>
          </div>
          {err && <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{err}</p>}
          <button className="btn-primary" disabled={busy}>{busy ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />} {t('adminCourses.create')}</button>
        </form>

        <section className="mt-8">
          <div className="flex flex-wrap items-center gap-3 mb-3">
            <SectionTitle icon={<Users size={15} />} tone="cobalt">{t('adminCourses.all', { n: courses?.length ?? 0 })}</SectionTitle>
            <label className="relative ml-auto w-full sm:w-72">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input className="input pl-9 h-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('adminCourses.search')} aria-label={t('adminCourses.search')} />
            </label>
          </div>
          {!courses ? <Loader2 className="animate-spin text-ink-muted" /> : shown.length === 0 ? (
            <EmptyState compact icon={<GraduationCap size={20} />} title={t('adminCourses.none')} text={t('adminCourses.noneHint')} />
          ) : (
            <ul className="grid md:grid-cols-2 gap-3">
              {shown.map((c) => (
                <li key={c.id} className={`card p-4 flex flex-col gap-2 ${c.archived ? 'opacity-60' : ''}`}>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] font-bold bg-ink text-white rounded px-1.5 py-0.5">{c.code}</span>
                    {c.semester && <span className="text-[12px] text-ink-muted">{c.semester}</span>}
                    {c.archived && <span className="text-[11px] font-semibold rounded-full bg-line-soft px-2 py-0.5">{t('adminCourses.archived')}</span>}
                    <button className="ml-auto btn-ghost btn-sm px-1.5 hover:text-bad" onClick={() => remove(c)} aria-label={t('adminCourses.delete')} title={t('adminCourses.delete')}><Trash2 size={14} /></button>
                  </div>
                  <Link to={`/courses/${c.id}`} className="font-bold text-[16px] hover:text-cobalt">{c.name}</Link>
                  <dl className="text-[12.5px] text-ink-muted grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-2 gap-y-0.5">
                    <dt>{t('courseRole.teacher')}</dt><dd className="text-ink-soft truncate">{c.teachers.join(', ') || '—'}</dd>
                    <dt>{t('courseRole.assistant')}</dt><dd className="text-ink-soft truncate">{c.assistants.join(', ') || '—'}</dd>
                    <dt>{t('courseRole.lab')}</dt><dd className="text-ink-soft truncate">{c.labs.join(', ') || '—'}</dd>
                    <dt>{t('courseRole.student')}</dt><dd className="text-ink-soft">{c.students}</dd>
                  </dl>
                  <Link to={`/courses/${c.id}?tab=students`} className="mt-1 self-start btn-secondary btn-sm"><Users size={14} /> {t('adminCourses.people')} <ArrowRight size={14} /></Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
