/** account types: student | teacher | admin ('assistant' / 'professor' are old names of a teacher account) */
export type UserRole = 'student' | 'teacher' | 'admin' | 'assistant' | 'professor'
/** a person's place in a subject's space; what a teacher may do there are their `permissions` */
export type CourseRole = 'teacher' | 'student'
export type Permission =
  | 'labs.view' | 'labs.manage' | 'labs.grade'
  | 'exams.view' | 'exams.manage' | 'exams.grade'
  | 'grades.view' | 'grades.final' | 'grades.rules'
  | 'people.view' | 'materials.manage' | 'mail.send' | 'activity.view' | 'practice.view'
export type PermTemplate = 'professor' | 'assistant' | 'lab'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  auth_provider?: 'password' | 'microsoft'
  created_at: string
  avatar_url?: string | null
}

export interface Profile {
  id: string
  name: string
  role: UserRole
  avatar_url: string | null
  email: string | null
  bio: string
  // staff
  title?: string
  office?: string
  consultation_hours?: string
  website?: string
  // students (only for themselves and their course staff)
  index_number?: string
  study_program?: string
  study_year?: number | null
  // own profile only
  show_email?: boolean
  email_reminders?: boolean
  auth_provider?: 'password' | 'microsoft'
}

/** Assistants, professors and admins author tasks. */
export const isStaff = (u?: User | null) => !!u && u.role !== 'student'
/** Professors and admins create courses. */
export const canCreateCourses = (_u?: User | null) => false   // sprint 21: every subject has its space; nothing to make

export interface Course {
  id: string
  code: string
  name: string
  semester: string
  description: string
  archived: boolean
  my_role: CourseRole
  /** what I may do here (a teacher: what the admin ticked; the admin: everything; a student: none) */
  permissions?: Permission[]
  template?: PermTemplate | null
  students: number
  join_code: string | null
  join_enabled: boolean | null
  next_due?: string | null
  // sprint 7
  language?: 'mk' | 'en'
  reminders_enabled?: boolean
  reminder_hours?: number
  /** the FINKI subject this course is a run of */
  subject_id?: string | null
}

export interface AssignmentTask {
  task_id: string
  title: string
  language: string
  points: number
  my_score?: number | null
  my_late?: boolean
  my_submissions?: number
  has_feedback?: boolean
  more_points?: boolean
  kind?: TaskKind
  rubric?: boolean
  variant_group?: number | null
}

export type AssignmentKind = 'lab' | 'homework' | 'practice' | 'exam'
export type AIMode = 'full' | 'hints' | 'off'
export type TaskKind = 'code' | 'document' | 'project' | 'offline'
export interface RubricItem { id: string; title: string; points: number }
export type ResultsVisibility = 'full' | 'summary' | 'none'
export type ExamState = 'not_started' | 'running' | 'over'
export type AssignmentStatus = 'draft' | 'scheduled' | 'open' | 'late' | 'closed'

export interface Assignment {
  id: string
  course_id: string
  title: string
  description: string
  kind: AssignmentKind
  group_id: string | null
  group_name: string | null
  opens_at: string | null
  due_at: string | null
  allow_late: boolean
  late_penalty: number
  published: boolean
  status: AssignmentStatus
  tasks: AssignmentTask[]
  max_points: number
  my_score?: number | null
  // sprint 4 settings
  ai_mode: AIMode
  hint_limit: number
  exam: boolean
  duration_minutes: number | null
  results_visibility: ResultsVisibility
  scores_after_publish: boolean
  grades_published: boolean
  ip_restricted: boolean
  review_threshold: number
  improve_limit: number
  category?: GradeCategory | 'none' | null
  practice_for?: 'k1' | 'k2' | 'exam' | null
  editor_checks?: boolean
  counts_as?: GradeCategory | 'none'
  allowed_ips?: string
  // students, exams
  exam_state?: ExamState
  attempt?: { started_at: string; ends_at: string | null; finished_at: string | null } | null
  ip_ok?: boolean
  task_count?: number
  // detail only
  course_name?: string
  course_code?: string
  my_role?: CourseRole
  permissions?: Permission[]
  server_time?: string
  students_submitted?: number
}

export interface CourseDetail extends Course {
  groups: { id: string; name: string; language?: 'mk' | 'en' | null }[]
  my_group: string | null
  assignments: Assignment[]
}

export interface CourseMember {
  user_id: string
  name: string
  email: string
  avatar_url?: string | null
  role: CourseRole
  permissions?: Permission[]
  template?: PermTemplate | null
  /** how a student got here: plan (mandatory subject / chosen elective) | admin | lti */
  source?: 'plan' | 'admin' | 'lti'
  account?: UserRole
  group_id: string | null
  group_name: string | null
  role_locked?: boolean   // set by the admin: Moodle (LTI) doesn't change it
  joined_at: string
}

export interface Gradebook {
  assignments: { id: string; title: string; kind: AssignmentKind; due_at: string | null; group_id: string | null; published: boolean; max_points: number; exam: boolean; grades_published: boolean }[]
  students: {
    user_id: string; name: string; email: string; group: string | null; total: number
    scores: Record<string, { score: number | null; late: boolean; applies: boolean }>
  }[]
}

export interface SubmitResult {
  submission_id: string
  status: 'pending' | 'running' | 'done' | 'error'
  queue_position?: number
  more_points: boolean
  visibility: ResultsVisibility
  passed: number | null
  total: number | null
  score: number | null
  max_points: number
  late: boolean
  late_penalty: number
  best_score: number | null
  submitted_at: string
  results: TestResult[]
}

export interface AIPolicy {
  mode: AIMode
  hint_limit: number | null
  hints_used: number
  hints_left: number | null
  assignment_id: string | null
  assignment_title: string | null
  improve_limit: number | null
  improve_left: number | null
  editor_checks?: boolean  // compiler errors underlined while typing (an exam can turn them off)
}

export interface LineComment { id?: string; line: number; path?: string; body: string; author?: string | null; created_at?: string }

export interface FileInfo { file_name: string; file_type: string; file_size: number }

export interface Upload extends FileInfo { id: string; late: boolean; submitted_at: string }

export interface SubmissionFull extends FileInfo {
  id: string; passed: number; total: number; score: number; late: boolean; submitted_at: string; code: string
  comments: LineComment[]; status: string
}

export interface Overview {
  assignment_id: string; title: string; exam: boolean; grades_published: boolean; max_points: number
  tasks: { task_id: string; title: string; points: number; kind: TaskKind; variant_group: number | null }[]
  students: {
    user_id: string; name: string; email: string; group: string | null; total: number | null
    to_review: number; attendance: 'present' | 'absent' | 'excused' | null
    tasks: { task_id: string; title: string; points: number; kind: TaskKind; auto: number | null; final: number | null; submissions: number;
      late: boolean; graded: boolean; comment: boolean; more_points: boolean; reviewed: boolean }[]
    attempt: { started_at: string; ends_at: string | null; finished_at: string | null; ip: string } | null
    signals: Record<string, number>
  }[]
}

export interface Review {
  student: { user_id: string; name: string; email: string }
  task: { task_id: string; title: string; language: string; points: number; kind: TaskKind; rubric: RubricItem[]
    reference_file: { name: string; size: number } | null }
  submissions: SubmissionFull[]
  best: number | null
  grade: { adjust: number; override: number | null; comment: string; rubric_scores: Record<string, number> | null; updated_at: string } | null
  final: number | null
  events: { kind: string; detail: string; ip: string; task_id: string | null; created_at: string }[]
}

export interface Feedback {
  points: number; kind: TaskKind; auto: number | null; final: number | null; adjust: number; override: number | null; comment: string
  rubric: RubricItem[]; rubric_scores: Record<string, number> | null
  submissions: (FileInfo & { id: string; score: number; passed: number; total: number; submitted_at: string; code: string; best: boolean; comments: LineComment[] })[]
}

export interface SimilarityReport {
  threshold: number
  tasks: {
    task_id: string; title: string; language: string; compared: number
    pairs: {
      a: { user_id: string; name: string; email: string; submission_id: string }
      b: { user_id: string; name: string; email: string; submission_id: string }
      similarity: number; lines_a: [number, number][]; lines_b: [number, number][]
      /** diagrams: elements both have beyond the model solution, and how alike the layout is (0..1, null = too few boxes) */
      shared?: string[] | null; layout?: number | null
    }[]
  }[]
}

export interface SubmissionItem {
  id: string
  task_id: string
  passed: number
  total: number
  score: number
  late: boolean
  submitted_at: string
  code: string
}

export interface AdminUser {
  id: string
  name: string
  email: string
  role: UserRole
  auth_provider: string
  created_at: string
}

export interface TestCase {
  id: string
  type: 'code_sample' | 'stdin_stdout' | 'diagram'
  test_code: string
  stdin: string
  expected_output: string
  order: number
  is_hidden?: boolean
}

export interface Task {
  id: string
  title: string
  description: string
  starter_code: string
  language: string
  created_at: string
  test_cases: TestCase[]
  hidden_tests?: number
  model_solution?: string
  is_public?: boolean
  kind?: TaskKind
  // task bank (staff)
  content_lang?: 'mk' | 'en'
  translations?: Partial<Record<'mk' | 'en', { title: string; description: string }>>
  rubric?: RubricItem[]
  reference_file?: { name: string; size: number; content_type: string } | null
  subject_id?: string | null
  /** an AI practice task made for this student */
  generated?: boolean
}

export interface TaskListItem {
  id: string
  title: string
  language: string
  kind?: TaskKind
  is_public?: boolean
  created_at: string
  subject_id?: string | null
}

export interface SessionStep {
  id: string
  step_number: number
  title: string
  description: string
  step_type: 'correctness' | 'optimization'
  status: 'pending' | 'active' | 'completed'
  agent_feedback: string
  /** why this step: its purpose / the idea behind it */
  why?: string
  /** one extra useful fact */
  tip?: string
}

/** Another way to solve a finished task ("write another solution"). */
export interface Alternative { title: string; idea: string }

export interface Session {
  id: string
  task_id: string
  status: 'in_progress' | 'completed'
  current_step: number
  current_code: string
  steps: SessionStep[]
  /** several solutions of one task: which one this is, its approach ("" = the first), what else is possible */
  solution_no?: number
  approach?: string
  alternatives?: Alternative[]
  created_at: string
  updated_at: string
}

export interface TestResult {
  test_number: number
  type: string
  test_code: string
  stdin: string
  expected_output: string
  actual_output: string
  passed: boolean
  error?: string
  hidden?: boolean
  /** web visual tests: screenshots of the student's page and of the model solution (data URLs) */
  images?: { actual: string; expected: string; viewport?: string } | null
}

export interface RunTestsResponse {
  results: TestResult[]
  total: number
  passed: number
  failed: number
}

export interface CheckStepResponse {
  passed: boolean
  feedback: string
  step_completed: boolean
  all_steps_completed: boolean
  next_step?: SessionStep | null
  alternatives?: Alternative[]
}

export type AIProvider = 'openai' | 'anthropic' | 'openai_compatible'

export interface AISettings {
  provider: AIProvider
  model: string
  base_url: string
  has_key: boolean
  key_hint: string
  source: 'env' | 'database'
  key_unreadable: boolean
}

export interface AITestResult {
  ok: boolean
  latency_ms: number
  reply?: string
  error?: string
}

export interface MonitoringData {
  range: '24h' | '7d' | '30d'
  bucket: 'hour' | 'day'
  generated_at: string
  ai_config: { provider: string; model: string; source: string; has_key: boolean }
  ai: { calls: number; errors: number; p50_ms: number; p95_ms: number; input_tokens: number; output_tokens: number }
  ai_by_operation: { operation: string; calls: number; errors: number; avg_ms: number; p95_ms: number; tokens: number }[]
  ai_by_model: { provider: string; model: string; calls: number; errors: number; p95_ms: number; input_tokens: number; output_tokens: number }[]
  timeline: { t: string; ai_ok: number; ai_errors: number; test_runs: number }[]
  tests_by_language: {
    language: string; runs: number; runner_errors: number; avg_ms: number; tests_passed: number; tests_total: number
    all_green_runs: number; runs_with_compile_errors: number
  }[]
  activity: {
    active_students: number; sessions_started: number; tasks_completed: number; step_checks: number; steps_passed: number
    rate_limited: number; rate_limited_students: number
  }
  limits: { ai_per_minute: number; ai_per_day: number; tests_per_minute: number }
  runner: { workers: number; busy: number; waiting: number; isolated: boolean } | null
  recent_errors: { created_at: string; kind: string; operation: string; provider: string; model: string; prog_language: string; error: string; request_id: string }[]
}

export interface ImportTestCase {
  type: 'code_sample' | 'stdin_stdout' | 'diagram'
  test_code: string
  stdin: string
  expected_output: string
  is_hidden: boolean
  order: number
}

export interface ImportQuestion {
  index: number
  title: string
  description: string
  starter_code: string
  model_solution: string
  language: string
  coderunner_type: string
  test_cases: ImportTestCase[]
  warnings: string[]
  duplicate: boolean
}

export interface ImportPreview {
  questions: ImportQuestion[]
  skipped: { title: string; reason: string; detail: string }[]
  suggested_subject_id: string | null
}

export interface VizField {
  name: string
  value: string
}

export interface VizStructure {
  name: string
  kind: 'stack' | 'array' | 'queue' | 'object' | 'value' | 'table'
  type: string
  items: string[]
  highlight: number[]
  fields: VizField[]
  value: string
  columns: string[] // table
  rows: string[][] // table
}

export interface VizFrame {
  line: number
  code: string
  explanation: string
  /** why this moment matters */
  why?: string
  /** an extra informative fact */
  tip?: string
  /** the structure being processed right now, and the item / field in it */
  focus?: string
  focus_index?: number
  focus_field?: string
  structures: VizStructure[]
  output: string
  exception: string
}

export interface TestVisualization {
  test_case_id: string
  frames: VizFrame[]
}

export type AgentMessageKind = 'action' | 'pass' | 'fail' | 'hint' | 'step' | 'done' | 'error' | 'note'

export interface AgentMessage {
  role: 'user' | 'assistant'
  kind?: AgentMessageKind
  title?: string
  content: string
  timestamp: Date
}

export interface SessionSummary {
  task_id: string
  session_id: string
  status: 'in_progress' | 'completed'
  current_step: number
  completed_steps: number
}

// ---------------------------------------------------------------------------
// Sprint 7: e-mail, materials, grading scheme and standing
// ---------------------------------------------------------------------------

export type GradeCategory = 'labs' | 'homework' | 'k1' | 'k2' | 'exam'
export type EmailKind = 'announcement' | 'deadline' | 'grades' | 'gradesheet' | 'reminder' | 'custom'
export type EmailStatus = 'draft' | 'sending' | 'sent' | 'cancelled'

export interface CourseEmail {
  id: string
  course_id: string
  kind: EmailKind
  audience: 'students' | 'staff'
  group_id: string | null
  assignment_id: string | null
  assignment_title: string | null
  subject_mk: string
  subject_en: string
  body_mk?: string
  body_en?: string
  status: EmailStatus
  created_at: string
  sent_at: string | null
  recipients: number
  failed: number
  automatic: boolean
  attachment_name: string | null
  would_reach?: { total: number; mk: number; en: number }
  deliveries?: { address: string; lang: string; status: 'queued' | 'sent' | 'preview' | 'failed'; error: string }[]
}

export interface Announcement {
  id: string
  subject: string
  body: string
  sent_at: string
  kind: EmailKind
  assignment_id: string | null
}

export interface CourseMaterial {
  id: string
  section: 'lecture' | 'exercise' | 'other'
  title: string
  week: number | null
  position: number
  published: boolean
  file_name: string
  file_type: string
  file_size: number
  has_preview: boolean
  created_at: string
}

export type RuleType = 'max_missed_labs' | 'min_labs_signature' | 'min_colloquium' | 'k1_exempt_qualifying' | 'signature_for_exam'
export interface GradingRule { type: RuleType; enabled: boolean; value: number | null }
export interface GradingScheme {
  weights: Record<GradeCategory, number>
  thresholds: number[]
  rules: GradingRule[]
}

export interface StandingReason { key: string; [k: string]: any }
export interface StudentStanding {
  user_id: string
  name: string
  email: string
  group: string | null
  index: string
  categories: Record<GradeCategory, { got: number; max: number; pct: number | null }>
  total: number
  missed_labs: number
  signature: boolean | null
  eligible_exam: boolean
  exempt: boolean | null
  colloquia: Record<string, { pct: number | null; passed: boolean | null }>
  grade: number | null
  final_grade?: number | null   // entered by the professor (grade is only the proposal)
  estimate?: GradeEstimate
  reasons: StandingReason[]
}
export interface CourseStanding {
  scheme: GradingScheme
  students: StudentStanding[]
  assignments: { id: string; category: GradeCategory | 'none'; counts: boolean }[]
}


/** A FINKI subject (предмет). */
export interface Subject {
  id: string
  code: string
  name: string
  name_mk: string
  name_en: string
  semester: number | null
  elective: boolean
  finki_code: string | null
  languages: string[]
  icon: string
  color: string
  description: string
}
export interface SubjectCourse { id: string; code: string; name: string; semester: string; my_role: CourseRole; permissions?: Permission[]; template?: PermTemplate | null; source?: string | null }
export interface SubjectSummary extends Subject { tasks: number; done: number; generated: number; courses: SubjectCourse[]; my_semester?: number | null }
export interface SubjectTask { id: string; title: string; language: string; created_at: string; status: 'in_progress' | 'completed' | null; current_step: number | null; is_public: boolean }
export interface SubjectDetail extends Subject { tasks: SubjectTask[]; generated: SubjectTask[]; courses: SubjectCourse[]; can_practice: boolean; staff?: boolean; space_id?: string | null; member?: boolean }

/** The grading tutor's suggestion (nothing is saved until the grader saves the points). */
export interface GradingSuggestion {
  points: number; max_points: number; rubric_scores: Record<string, number> | null; summary: string
  strengths: string[]; issues: { line: number | null; note: string }[]; comment: string; submission_id: string
}

/** "If you keep going like this": per weighted part the real % or what the student practised for it. */
export interface GradeEstimate {
  grade: number | null; total: number | null; own: number | null
  parts: Partial<Record<GradeCategory, { pct: number | null; source: 'real' | 'prep' | 'open' | 'own' | null }>>
}

/** A student's electives: chosen once freely, then changed only through a request to the admin. */
export interface ElectiveSide { subject_id: string; name: string; code: string; semester: number }
export interface ElectiveRequest {
  id: string; status: 'pending' | 'approved' | 'rejected' | 'cancelled'; reason: string; admin_note: string
  created_at: string; decided_at: string | null; remove: ElectiveSide; add: ElectiveSide; move: boolean
  student?: { user_id: string; name: string; email: string }; current?: { subject_id: string; semester: number }[]
}
export interface ElectivePlan {
  confirmed: boolean; confirmed_at: string | null; choices: { subject_id: string; semester: number }[]
  pending: ElectiveRequest | null; requests: ElectiveRequest[]
}
export interface StudentPractice {
  students: { user_id: string; name: string; email: string; done: number; tasks: SubjectTask[] }[]; tasks: number
}
export interface PracticeWork {
  task_id: string; title: string; language: string; student: { user_id: string; name: string; email: string }
  status: 'in_progress' | 'completed' | null; code: string; updated_at: string | null; steps: { n: number; title: string; status: string }[]
}

/** One entry of the logs (an AI call, a test run, something a person did). */
export interface LogItem {
  id: number; at: string; kind: 'ai' | 'tests' | 'activity' | 'limit' | 'audit'; operation: string; ok: boolean
  duration_ms: number; language: string | null
  user?: { id: string; name: string; email: string; role: string; course_role?: string | null } | null
  about?: string   // the other person the action was about (a student graded, a member changed)
  task: { id: string; title: string } | null; course: { id: string; code: string; name: string } | null
  session_id: string | null; extra: Record<string, any>; error: string | null
  provider?: string | null; model?: string | null; input_tokens?: number; output_tokens?: number; request_id?: string | null
}
export interface LogPage {
  items: LogItem[]; next_before: number | null
  operations?: { operation: string; kind: string; count: number; errors: number }[]
  totals?: Record<string, number>
}
