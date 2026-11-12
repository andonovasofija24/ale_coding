/** What a teacher may do in a subject (the same list as backend/app/core/permissions.py). */
import type { AssignmentKind, Permission, PermTemplate } from '../types'

export const PERM_GROUPS: { key: 'labs' | 'exams' | 'grades' | 'other'; perms: Permission[] }[] = [
  { key: 'labs', perms: ['labs.view', 'labs.manage', 'labs.grade'] },
  { key: 'exams', perms: ['exams.view', 'exams.manage', 'exams.grade'] },
  { key: 'grades', perms: ['grades.view', 'grades.final', 'grades.rules'] },
  { key: 'other', perms: ['people.view', 'materials.manage', 'mail.send', 'activity.view', 'practice.view'] },
]
export const ALL_PERMS: Permission[] = PERM_GROUPS.flatMap((g) => g.perms)

export const TEMPLATES: Record<PermTemplate, Permission[]> = {
  professor: ALL_PERMS,
  assistant: ['labs.view', 'labs.manage', 'labs.grade', 'exams.view', 'exams.manage', 'exams.grade', 'grades.view',
              'people.view', 'materials.manage', 'mail.send', 'activity.view', 'practice.view'],
  lab: ['labs.view', 'labs.manage', 'labs.grade', 'practice.view'],
}

/** *.manage / *.grade imply *.view; final grades and rules imply seeing the points */
export function cleanPerms(p: Iterable<Permission>): Permission[] {
  const s = new Set(p)
  for (const g of ['labs', 'exams'] as const) if (s.has(`${g}.manage`) || s.has(`${g}.grade`)) s.add(`${g}.view`)
  if (s.has('grades.final') || s.has('grades.rules')) s.add('grades.view')
  return ALL_PERMS.filter((x) => s.has(x))
}

export function templateOf(p: Permission[] | undefined | null): PermTemplate | null {
  const s = new Set(p ?? [])
  for (const [k, v] of Object.entries(TEMPLATES)) if (v.length === s.size && v.every((x) => s.has(x))) return k as PermTemplate
  return null
}

type HasPerms = { permissions?: Permission[] | null } | null | undefined
export const can = (x: HasPerms, perm: Permission) => !!x?.permissions?.includes(perm)
export const groupOfKind = (k: AssignmentKind) => (k === 'lab' || k === 'practice' ? 'labs' : 'exams')
export const canKind = (x: HasPerms, k: AssignmentKind, action: 'view' | 'manage' | 'grade') =>
  can(x, `${groupOfKind(k)}.${action}` as Permission)
