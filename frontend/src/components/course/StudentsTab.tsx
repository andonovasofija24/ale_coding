import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Info, Loader2, Lock, Plus, Trash2, UserMinus, UserPlus } from 'lucide-react'
import { coursesApi } from '../../services/api'
import Avatar from '../Avatar'
import { useLanguage } from '../../i18n/LanguageContext'
import { useAuth } from '../../contexts/AuthContext'
import { CourseDetail, CourseMember, CourseRole } from '../../types'
import MoodleCard from './MoodleCard'

/** The people of a course. The admin puts people in (by e-mail, with their role), makes groups and changes roles;
 *  the professor and assistants see the list. There is no joining with a code. */
export default function StudentsTab({ course }: { course: CourseDetail }) {
  const { t, tError } = useLanguage()
  const { user } = useAuth()
  const qc = useQueryClient()
  const teacher = course.my_role === 'teacher'
  const admin = user?.role === 'admin'   // only the admin manages people and groups
  const { data: members = [], isLoading } = useQuery<CourseMember[]>({
    queryKey: ['members', course.id], queryFn: () => coursesApi.members(course.id),
  })
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['members', course.id] })
    qc.invalidateQueries({ queryKey: ['course', course.id] })
  }

  const [groupName, setGroupName] = useState('')
  const [groupLang, setGroupLang] = useState<'' | 'mk' | 'en'>('')
  const [emails, setEmails] = useState('')
  const [addRole, setAddRole] = useState<CourseRole>('student')
  const [addGroup, setAddGroup] = useState('')
  const [adding, setAdding] = useState(false)
  const [addResult, setAddResult] = useState<{ added: string[]; already: string[]; not_found: string[] } | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')

  const act = async (fn: () => Promise<unknown>) => {
    setError('')
    try { await fn(); refresh() } catch (err: any) { setError(tError(err.response?.data?.detail, 'course.actionFailed')) }
  }


  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    const list = emails.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean)
    if (!list.length) return
    setAdding(true); setError(''); setAddResult(null)
    try {
      setAddResult(await coursesApi.addMembers(course.id, { emails: list, role: addRole, group_id: addGroup || null }))
      setEmails('')
      refresh()
    } catch (err: any) {
      setError(tError(err.response?.data?.detail, 'course.actionFailed'))
    } finally { setAdding(false) }
  }

  const staff = members.filter((m) => m.role !== 'student')
  const students = members.filter((m) => m.role === 'student' &&
    (!filter || (filter === '__none' ? !m.group_id : m.group_id === filter)))

  return (
    <div className="space-y-6">
      {error && <p role="alert" className="text-sm text-bad bg-bad-soft rounded-lg px-3 py-2">{error}</p>}
      <MoodleCard courseId={course.id} teacher={teacher} />

      {!admin && (
        <p className="card px-4 py-3 text-[13px] text-ink-muted flex items-center gap-2"><Info size={15} className="shrink-0" /> {t('course.peopleByAdmin')}</p>
      )}
      <div className="grid gap-4">
        {/* Groups */}
        <section className="card p-5">
          <h2 className="font-bold">{t('course.groups')}</h2>
          <p className="mt-1 text-[13px] text-ink-muted">{t('course.groupsHint')} {t('course.groupLangHint')}</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {course.groups.map((g) => (
              <li key={g.id} className="inline-flex items-center gap-1 text-[13px] font-semibold bg-obj-soft text-obj rounded-full pl-3 pr-1 py-0.5">
                {g.name}
                <span className="text-obj/60 font-normal">· {members.filter((m) => m.group_id === g.id && m.role === 'student').length}</span>
                {admin && <><select value={g.language ?? ''} title={t('course.groupLanguage')} aria-label={t('course.groupLanguage')}
                  onChange={(e) => act(() => coursesApi.renameGroup(course.id, g.id, g.name, (e.target.value || null) as any))}
                  className="ml-1 bg-transparent text-[11px] font-bold uppercase text-obj/80 rounded hover:bg-obj/10 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-obj/40">
                  <option value="">{(course.language || 'mk').toUpperCase()}</option>
                  <option value="mk">MK</option>
                  <option value="en">EN</option>
                </select>
                <button onClick={() => confirm(t('course.deleteGroupConfirm', { name: g.name })) && act(() => coursesApi.deleteGroup(course.id, g.id))}
                  className="w-6 h-6 rounded-full inline-flex items-center justify-center hover:bg-obj/10" aria-label={t('course.deleteGroup')}>
                  <Trash2 size={12} />
                </button></>}
              </li>
            ))}
            {course.groups.length === 0 && <li className="text-[13px] text-ink-faint">{t('course.noGroups')}</li>}
          </ul>
          {admin && <form className="mt-3 flex gap-2" onSubmit={(e) => {
            e.preventDefault()
            if (groupName.trim()) act(() => coursesApi.addGroup(course.id, groupName.trim(), groupLang || null)).then(() => { setGroupName(''); setGroupLang('') })
          }}>
            <input value={groupName} onChange={(e) => setGroupName(e.target.value)} className="input h-9" placeholder={t('course.groupPlaceholder')} maxLength={200} />
            <select value={groupLang} onChange={(e) => setGroupLang(e.target.value as any)} className="input h-9 w-auto text-[13px]" aria-label={t('course.groupLanguage')}>
              <option value="">{t('course.groupLangDefault')}</option>
              <option value="mk">{t('course.langMk')}</option>
              <option value="en">{t('course.langEn')}</option>
            </select>
            <button type="submit" className="btn-secondary btn-sm h-9" disabled={!groupName.trim()}><Plus size={14} /> {t('course.addGroup')}</button>
          </form>}
        </section>
      </div>

      {/* Add by e-mail (admin) */}
      {admin && <section className="card p-5">
        <h2 className="font-bold flex items-center gap-2"><UserPlus size={17} /> {t('course.addPeople')}</h2>
        <p className="mt-1 text-[13px] text-ink-muted">{t('course.addPeopleHint')}</p>
        <form onSubmit={add} className="mt-3 grid md:grid-cols-[minmax(0,1fr)_11rem_12rem_auto] gap-2 items-start">
          <textarea value={emails} onChange={(e) => setEmails(e.target.value)} rows={2} className="input h-auto py-2 font-mono text-[13px]"
            placeholder="ana.petrovska@students.finki.ukim.mk, marko@students.finki.ukim.mk" />
          <select value={addRole} onChange={(e) => setAddRole(e.target.value as CourseRole)} className="input" aria-label={t('course.role')}>
            <option value="student">{t('courseRole.student')}</option>
            <option value="lab">{t('courseRole.lab')}</option>
            <option value="assistant">{t('courseRole.assistant')}</option>
            <option value="teacher">{t('courseRole.teacher')}</option>
          </select>
          <select value={addGroup} onChange={(e) => setAddGroup(e.target.value)} className="input" aria-label={t('course.group')}>
            <option value="">{t('course.noGroup')}</option>
            {course.groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
          <button type="submit" disabled={adding || !emails.trim()} className="btn-primary">
            {adding && <Loader2 size={15} className="animate-spin" />} {t('course.add')}
          </button>
        </form>
        {addResult && (
          <div className="mt-3 text-[13px] space-y-1">
            {addResult.added.length > 0 && <p className="text-ok">{t('course.addedN', { n: addResult.added.length })}</p>}
            {addResult.already.length > 0 && <p className="text-ink-muted">{t('course.alreadyN', { n: addResult.already.length })}</p>}
            {addResult.not_found.length > 0 && (
              <p className="text-bad">{t('course.notFoundEmails')} <span className="font-mono">{addResult.not_found.join(', ')}</span></p>
            )}
          </div>
        )}
      </section>}

      {/* Members */}
      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="panel-title">{t('course.members')}</h2>
          {course.groups.length > 0 && (
            <select value={filter} onChange={(e) => setFilter(e.target.value)} className="input h-8 w-auto text-[13px]" aria-label={t('course.group')}>
              <option value="">{t('course.allGroups')}</option>
              {course.groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
              <option value="__none">{t('course.noGroup')}</option>
            </select>
          )}
        </div>
        {isLoading ? (
          <div className="mt-6 flex justify-center text-ink-muted"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="mt-3 card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[12px] text-ink-muted border-b border-line-soft">
                  <th className="px-4 py-2.5 font-semibold">{t('course.name')}</th>
                  <th className="px-4 py-2.5 font-semibold">{t('course.role')}</th>
                  <th className="px-4 py-2.5 font-semibold">{t('course.group')}</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {[...staff, ...students].map((m) => (
                  <tr key={m.user_id}>
                    <td className="px-4 py-2.5">
                      <Link to={`/users/${m.user_id}`} className="group flex items-center gap-2.5">
                        <Avatar name={m.name} url={m.avatar_url} size={30} />
                        <span className="min-w-0">
                          <span className="block font-medium group-hover:text-cobalt">{m.name}</span>
                          <span className="block text-[12px] text-ink-muted">{m.email}</span>
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      {admin && m.user_id !== user?.id ? (
                        <select value={m.role} className="input h-8 w-auto text-[13px]"
                          onChange={(e) => act(() => coursesApi.updateMember(course.id, m.user_id, { role: e.target.value }))}>
                          <option value="student">{t('courseRole.student')}</option>
                          <option value="lab">{t('courseRole.lab')}</option>
                          <option value="assistant">{t('courseRole.assistant')}</option>
                          <option value="teacher">{t('courseRole.teacher')}</option>
                        </select>
                      ) : (
                        <span className="text-[13px]">{t(`courseRole.${m.role}` as any)}</span>
                      )}
                      {m.role_locked && (admin ? (
                        <button type="button" className="ml-1.5 align-middle text-ink-muted hover:text-ink" title={t('course.roleLockedUnlock')}
                          aria-label={t('course.roleLockedUnlock')}
                          onClick={() => act(() => coursesApi.updateMember(course.id, m.user_id, { unlock_role: true }))}><Lock size={13} /></button>
                      ) : <Lock size={13} className="ml-1.5 inline align-middle text-ink-muted" aria-label={t('course.roleLocked')} />)}
                    </td>
                    <td className="px-4 py-2.5">
                      {m.role === 'student' ? (
                        <select value={m.group_id ?? ''} className="input h-8 w-auto text-[13px]"
                          onChange={(e) => act(() => coursesApi.updateMember(course.id, m.user_id,
                            e.target.value ? { group_id: e.target.value } : { clear_group: true }))}>
                          <option value="">{t('course.noGroup')}</option>
                          {course.groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                        </select>
                      ) : <span className="text-ink-faint">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {admin && m.user_id !== user?.id && (
                        <button className="btn-ghost btn-sm px-2 text-ink-muted hover:text-bad" title={t('course.remove')} aria-label={t('course.remove')}
                          onClick={() => confirm(t('course.removeConfirm', { name: m.name })) && act(() => coursesApi.removeMember(course.id, m.user_id))}>
                          <UserMinus size={15} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {students.length === 0 && staff.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-ink-muted">{t('course.noMembers')}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
