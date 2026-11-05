/**
 * Guided tours ("демо") for newcomers. A tour is a list of steps; each step points at an element marked with
 * data-tour="…" (and, if needed, first goes to a page). Without a target the step is a centred card (the welcome).
 * Texts: tour.<step>.title / tour.<step>.body in i18n/translations.ts.
 *
 * The main tour of a role starts by itself the first time someone signs in; the task tour the first time they
 * open a task; the course tour the first time staff open a course. The "Водич" button in the top bar replays the
 * tour of the page you are on.
 */
import type { UserRole } from '../types'

export interface TourStep {
  /** the i18n key part: tour.<key>.title / tour.<key>.body */
  key: string
  /** data-tour value of the element to show; none = a card in the middle */
  target?: string
  /** go to this page first */
  path?: string
  /** a lucide icon name for the card */
  icon?: string
}

const profileSteps = (staff: boolean): TourStep[] => [
  { key: 'profile', target: 'profile-avatar', path: '/profile', icon: 'user' },
  { key: staff ? 'profileFactsStaff' : 'profileFacts', target: 'profile-facts', path: '/profile', icon: 'id' },
  { key: 'ownKey', target: 'own-key', path: '/profile', icon: 'key' },
]

export const TOURS: Record<string, TourStep[]> = {
  student: [
    { key: 'welcomeStudent', icon: 'sparkles' },
    { key: 'navSubjects', target: 'nav-courses', path: '/courses', icon: 'cap' },
    { key: 'console', target: 'home-console', path: '/courses', icon: 'terminal' },
    { key: 'catalog', target: 'subjects', path: '/courses', icon: 'library' },
    ...profileSteps(false),
    { key: 'language', target: 'lang-switch', icon: 'languages' },
    { key: 'help', target: 'help', icon: 'compass' },
    { key: 'doneStudent', icon: 'flag' },
  ],
  professor: [
    { key: 'welcomeStaff', icon: 'sparkles' },
    { key: 'navSubjects', target: 'nav-courses', path: '/courses', icon: 'cap' },
    { key: 'consoleStaff', target: 'home-console', path: '/courses', icon: 'terminal' },
    { key: 'catalogStaff', target: 'subjects', path: '/courses', icon: 'library' },
    { key: 'bank', target: 'nav-bank', icon: 'book' },
    ...profileSteps(true),
    { key: 'help', target: 'help', icon: 'compass' },
    { key: 'doneStaff', icon: 'flag' },
  ],
  assistant: [
    { key: 'welcomeStaff', icon: 'sparkles' },
    { key: 'navSubjects', target: 'nav-courses', path: '/courses', icon: 'cap' },
    { key: 'consoleStaff', target: 'home-console', path: '/courses', icon: 'terminal' },
    { key: 'catalogStaff', target: 'subjects', path: '/courses', icon: 'library' },
    { key: 'bank', target: 'nav-bank', icon: 'book' },
    ...profileSteps(true),
    { key: 'help', target: 'help', icon: 'compass' },
    { key: 'doneStaff', icon: 'flag' },
  ],
  admin: [
    { key: 'welcomeAdmin', icon: 'sparkles' },
    { key: 'navSubjects', target: 'nav-courses', path: '/courses', icon: 'cap' },
    { key: 'consoleAdmin', target: 'home-console', path: '/courses', icon: 'terminal' },
    { key: 'bank', target: 'nav-bank', icon: 'book' },
    { key: 'adminArea', target: 'admin-link', icon: 'settings' },
    ...profileSteps(true),
    { key: 'help', target: 'help', icon: 'compass' },
    { key: 'doneStaff', icon: 'flag' },
  ],
  task: [
    { key: 'taskDescription', target: 'task-description', icon: 'file' },
    { key: 'taskExamples', target: 'task-examples', icon: 'eye' },
    { key: 'taskEditor', target: 'task-editor', icon: 'code' },
    { key: 'taskRun', target: 'task-run', icon: 'terminal' },
    { key: 'taskTests', target: 'task-tests', icon: 'flask' },
    { key: 'taskTutor', target: 'task-tabs', icon: 'route' },
    { key: 'taskStart', target: 'task-start', icon: 'play' },
  ],
  courseStaff: [
    { key: 'courseTabs', target: 'course-tabs', icon: 'tabs' },
    { key: 'assignNew', target: 'assign-new', icon: 'plus' },
    { key: 'courseStudents', target: 'course-tabs', icon: 'users' },
  ],
  courseLab: [
    { key: 'courseLab', target: 'course-tabs', icon: 'tabs' },
    { key: 'labAssignments', target: 'assignments-list', icon: 'clipboard' },
  ],
}

export const mainTour = (role: UserRole) => (role === 'student' ? 'student' : role)

const KEY = (tour: string, uid: string) => `ale-tour:${tour}:${uid}`
export function tourDone(tour: string, uid: string): boolean {
  try { return localStorage.getItem(KEY(tour, uid)) === 'done' } catch { return true }
}
export function markTourDone(tour: string, uid: string) {
  try { localStorage.setItem(KEY(tour, uid), 'done') } catch { /* ignore */ }
}
