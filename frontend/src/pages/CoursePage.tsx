import { Link, useParams, useSearchParams } from 'react-router-dom'
import { can } from '../lib/perms'
import { permLabel } from '../components/PermissionsEditor'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Award, BookOpen, ChevronRight, ClipboardList, Loader2, Mail, Megaphone, Settings, Table2, Users, ScrollText } from 'lucide-react'
import { coursesApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { usePageTour } from '../components/Tour'
import { useLanguage } from '../i18n/LanguageContext'
import { Assignment, CourseDetail } from '../types'
import AppHeader from '../components/AppHeader'
import LangChip from '../components/LangChip'
import CodeBackdrop from '../components/CodeBackdrop'
import { LANG_ORDER } from '../lib/languages'
import { Deadline, KindBadge, Points, StatusBadge, fmt } from '../components/course/bits'
import AssignmentsTab from '../components/course/AssignmentsTab'
import StudentsTab from '../components/course/StudentsTab'
import GradebookTab from '../components/course/GradebookTab'
import LogView from '../components/LogView'
import SettingsTab from '../components/course/SettingsTab'
import MailTab from '../components/course/MailTab'
import MaterialsTab from '../components/course/MaterialsTab'
import Announcements from '../components/course/Announcements'
import { MyStanding } from '../components/course/Standing'
import { standingApi } from '../services/api'
import type { StudentStanding } from '../types'

type Tab = 'assignments' | 'students' | 'grades' | 'materials' | 'mail' | 'settings' | 'notices' | 'standing' | 'logs'

/** A course: students see their assignments; staff manage assignments, students, grades and settings. */
export default function CoursePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const { t } = useLanguage()
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const { data: course, isLoading, isError } = useQuery<CourseDetail>({
    queryKey: ['course', courseId], queryFn: () => coursesApi.get(courseId!), enabled: !!courseId,
  })
  // staff: a short tour of the course page the first time (a лаборант gets their own)
  const role = course?.my_role
  const onlyLabs = !!course && role === 'teacher' && !can(course, 'exams.view') && !can(course, 'grades.view')
  usePageTour(onlyLabs ? 'courseLab' : role === 'teacher' ? 'courseStaff' : null, !!course)

  if (isLoading) return <Shell><div className="flex justify-center py-20 text-ink-muted"><Loader2 className="animate-spin" /></div></Shell>
  if (isError || !course) return <Shell><p className="py-20 text-center text-ink-muted">{t('courses.notFound')}</p></Shell>

  const staff = course.my_role !== 'student'
  // languages used in this course's assignments colour the header; a new course shows them all
  const used = [...new Set(course.assignments.flatMap((x) => x.tasks.map((y) => y.language)))]
  const courseLangs = used.length ? used : LANG_ORDER
  const tab = (params.get('tab') as Tab) || 'assignments'
  // a teacher sees the tabs their permissions in this subject open (the admin: all of them)
  const tabs: { key: Tab; label: string; icon: JSX.Element }[] = staff ? [
    { key: 'assignments', label: t('course.tabAssignments'), icon: <ClipboardList size={15} /> },
    ...(can(course, 'people.view') ? [{ key: 'students' as Tab, label: t('course.tabStudents'), icon: <Users size={15} /> }] : []),
    ...(can(course, 'grades.view') ? [{ key: 'grades' as Tab, label: t('course.tabGrades'), icon: <Table2 size={15} /> }] : []),
    { key: 'materials', label: t('course.tabMaterials'), icon: <BookOpen size={15} /> },
    ...(can(course, 'mail.send') ? [{ key: 'mail' as Tab, label: t('course.tabMail'), icon: <Mail size={15} /> }] : []),
    ...(can(course, 'activity.view') ? [{ key: 'logs' as Tab, label: t('course.tabLogs'), icon: <ScrollText size={15} /> }] : []),
    ...(user?.role === 'admin' ? [{ key: 'settings' as Tab, label: t('course.tabSettings'), icon: <Settings size={15} /> }] : []),
  ] : [
    { key: 'assignments', label: t('course.tabAssignments'), icon: <ClipboardList size={15} /> },
    { key: 'materials', label: t('course.tabMaterials'), icon: <BookOpen size={15} /> },
    { key: 'notices', label: t('course.tabNotices'), icon: <Megaphone size={15} /> },
    { key: 'standing', label: t('course.tabStanding'), icon: <Award size={15} /> },
  ]

  return (
    <Shell>
      <Link to="/courses" className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">
        <ArrowLeft size={15} /> {t('courses.all')}
      </Link>
      {course.subject_id && <Link to={`/subjects/${course.subject_id}`} className="ml-4 inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink">{t('space.toSubject')}</Link>}
      <header className="mt-3 relative overflow-hidden rounded-2xl bg-ink text-white px-6 py-7 sm:px-8 sm:py-9">
        <CodeBackdrop langs={courseLangs} columns={4}
          className="[mask-image:linear-gradient(to_right,transparent_35%,black_85%)] sm:[mask-image:linear-gradient(to_right,transparent,black_45%,black)] opacity-90" />
        <div className="relative">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-bold bg-white text-ink rounded px-1.5 py-0.5">{course.code}</span>
            {course.semester && <span className="text-sm text-white/70">{course.semester}</span>}
            {course.archived && <span className="text-[11px] font-semibold bg-white/15 rounded-full px-2 py-0.5">{t('courses.archivedBadge')}</span>}
          </div>
          <h1 className="mt-2 text-3xl sm:text-4xl font-extrabold tracking-tight max-w-2xl">{course.name}</h1>
          {!staff && course.my_group && <p className="mt-1.5 text-sm text-white/70">{t('course.myGroup', { group: course.my_group })}</p>}
          {!staff && tab !== 'standing' && <EstimateBadge courseId={course.id} onOpen={() => setParams({ tab: 'standing' }, { replace: true })} />}
          {staff && <p className="mt-1.5 text-sm text-white/70">{(course.students === 1 ? t('courses.studentOne') : t('courses.studentsN', { n: course.students }))} · {permLabel(course.template, t)}</p>}
          {courseLangs.length > 0 && courseLangs.length < LANG_ORDER.length && (
            <div className="mt-3 flex flex-wrap gap-1.5">{courseLangs.map((l) => <LangChip key={l} lang={l} />)}</div>
          )}
        </div>
      </header>

      <>
          <nav className="mt-6 border-b-2 border-line flex gap-1 overflow-x-auto" aria-label={course.name} data-tour="course-tabs">
            {tabs.map((tb) => (
              <button key={tb.key} onClick={() => setParams({ tab: tb.key }, { replace: true })}
                className={`h-11 px-3 flex items-center gap-1.5 text-sm font-semibold border-b-2 -mb-px whitespace-nowrap transition-colors ${
                  tab === tb.key ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink'}`}>
                {tb.icon} {tb.label}
              </button>
            ))}
          </nav>
          <div className="mt-6">
            {tab === 'assignments' && (staff ? <AssignmentsTab course={course} /> : <StudentAssignments course={course} />)}
            {tab === 'students' && can(course, 'people.view') && <StudentsTab course={course} />}
            {tab === 'grades' && can(course, 'grades.view') && <GradebookTab course={course} />}
            {tab === 'materials' && <MaterialsTab course={course} />}
            {tab === 'mail' && can(course, 'mail.send') && <MailTab course={course} />}
            {tab === 'logs' && can(course, 'activity.view') && <><p className="mb-4 text-sm text-ink-muted max-w-3xl">{t('log.hintCourse')}</p><LogView mode="course" courseId={course.id} /></>}
            {tab === 'settings' && user?.role === 'admin' && <SettingsTab course={course} />}
            {tab === 'notices' && !staff && <Announcements courseId={course.id} />}
            {tab === 'standing' && !staff && <MyStanding courseId={course.id} />}
          </div>
      </>
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-10">{children}</main>
    </div>
  )
}

function StudentAssignments({ course }: { course: CourseDetail }) {
  const { t } = useLanguage()
  const assignments = course.assignments
  const current = assignments.filter((a) => a.status === 'open' || a.status === 'late')
  const past = assignments.filter((a) => a.status === 'closed')
  if (assignments.length === 0) {
    return <div className="card px-6 py-12 text-center text-ink-muted">{t('course.noAssignments')}</div>
  }
  return (
    <div className="space-y-8">
      <LatestNotice courseId={course.id} />
      {current.length > 0 && <AssignmentList title={t('course.current')} items={current} />}
      {past.length > 0 && <AssignmentList title={t('course.past')} items={past} />}
    </div>
  )
}

function AssignmentList({ title, items }: { title: string; items: Assignment[] }) {
  const { t } = useLanguage()
  return (
    <section>
      <h2 className="panel-title mb-3">{title}</h2>
      <ul className="card divide-y divide-line-soft overflow-hidden">
        {items.map((a) => (
          <li key={a.id}>
            <Link to={`/assignments/${a.id}`} className="group flex items-center gap-4 px-4 sm:px-5 py-4 hover:bg-paper/60 transition-colors">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <KindBadge kind={a.kind} />
                  <StatusBadge status={a.status} />
                  {a.exam && a.exam_state === 'running' && <span className="text-[11px] font-semibold bg-cobalt text-white rounded-full px-2 py-0.5">{t('exam.inProgress')}</span>}
                </div>
                <p className="mt-1 font-semibold group-hover:text-cobalt">{a.title}</p>
                <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <Deadline a={a} />
                  <span className="flex gap-1">{[...new Set(a.tasks.map((x) => x.language))].map((l) => <LangChip key={l} lang={l} />)}</span>
                </div>
              </div>
              {a.scores_after_publish && !a.grades_published ? <span className="text-[12px] text-ink-muted">/ {fmt(a.max_points)}</span>
                : <Points got={a.my_score ?? null} max={a.max_points} />}
              <ChevronRight size={16} className="text-ink-faint group-hover:text-cobalt" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

/** The newest notice, above the assignments (all of them are in the "Notices" tab). */
function LatestNotice({ courseId }: { courseId: string }) {
  return <Announcements courseId={courseId} limit={1} />
}


/** A student's estimated grade, right in the subject's header: ALE is for practice, so it is there at once (the real
 *  grade is the one a teacher enters). Opens the standing. */
function EstimateBadge({ courseId, onOpen }: { courseId: string; onOpen: () => void }) {
  const { t } = useLanguage()
  const { data } = useQuery<{ me: StudentStanding | null }>({
    queryKey: ['standing', courseId, 'me'], queryFn: () => standingApi.standing(courseId),
  })
  const me = data?.me
  if (!me) return null
  const final = me.final_grade ?? null
  const grade = final ?? me.estimate?.grade ?? null
  return (
    <button type="button" onClick={onOpen}
      className="mt-4 inline-flex items-center gap-3 rounded-xl bg-white/10 hover:bg-white/15 px-3.5 py-2 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/70">
      <span className={`inline-flex w-10 h-10 items-center justify-center rounded-full text-xl font-extrabold ${
        final != null ? 'bg-white text-ink' : 'border-2 border-dashed border-white/60'}`}>{grade ?? '—'}</span>
      <span className="text-[13px] leading-snug">
        <span className="block font-semibold">{final != null ? t('est.badgeFinal') : t('est.title')}</span>
        <span className="block text-white/65">{final != null ? t('est.badgeFinalHint') : grade != null ? t('est.badgeHint', { total: (me.estimate?.total ?? 0).toLocaleString() }) : t('est.notYet')}</span>
      </span>
    </button>
  )
}
