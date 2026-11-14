import axios from 'axios'
import { getStoredLang } from '../i18n/LanguageContext'
import type { GradingSuggestion } from '../types'

export const API_BASE = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ale_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  // Tells the backend which language the AI agent should answer in
  config.headers['Accept-Language'] = getStoredLang()
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ale_token')
      localStorage.removeItem('ale_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Auth
export const authApi = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post('/auth/register', data).then((r) => r.data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data).then((r) => r.data),
  me: () => api.get('/auth/me').then((r) => r.data),
}

// Tasks (student)
export const tasksApi = {
  list: () => api.get('/tasks').then((r) => r.data),
  get: (id: string) => api.get(`/tasks/${id}`).then((r) => r.data),
  visualize: (taskId: string, tcId: string) =>
    api.post(`/tasks/${taskId}/test-cases/${tcId}/visualize`).then((r) => r.data),
  /** How much the AI tutor may help right now (an assignment can limit it to hints or turn it off). */
  aiPolicy: (id: string) => api.get(`/tasks/${id}/ai-policy`).then((r) => r.data),
  /** A hint for the whole task; counted when the assignment allows only a few. */
  hint: (id: string, code: string): Promise<{ hint: string; hints_left: number | null }> =>
    api.post(`/tasks/${id}/hint`, { code }).then((r) => r.data),
  /** AI suggestions for a solution that already passes every test. */
  improve: (id: string, code: string): Promise<{ suggestions: string; improve_left: number | null }> =>
    api.post(`/tasks/${id}/improve`, { code }).then((r) => r.data),
  /** Diagram tasks: a picture / PDF of the student's own drawing, read into the editor by AI (exactly as drawn). */
  readDiagram: (id: string, file: File): Promise<{ upload_id: string; file_name: string; diagram: string; nodes: number; edges: number }> => {
    const form = new FormData(); form.append('file', file)
    return api.post(`/tasks/${id}/diagram/read`, form).then((r) => r.data)
  },
  diagramUploadUrl: async (uploadId: string) => {
    const r = await api.get(`/diagram-uploads/${uploadId}`, { responseType: 'blob' })
    return URL.createObjectURL(r.data)
  },
  /** Compiler errors / warnings for the editor (compiled on the server, never run). */
  check: (id: string, code: string) => api.post(`/tasks/${id}/check`, { code }).then((r) => r.data),
}

// Sessions
export const sessionsApi = {
  /** `code` = what is already in the editor; a new session starts from it instead of the starter code. */
  start: (taskId: string, code?: string) => api.post('/sessions', { task_id: taskId, code }).then((r) => r.data),
  mine: () => api.get('/sessions/mine').then((r) => r.data),
  overview: () => api.get('/sessions/overview').then((r) => r.data),
  getForTask: (taskId: string) => api.get(`/sessions/task/${taskId}`).then((r) => r.data),
  get: (id: string) => api.get(`/sessions/${id}`).then((r) => r.data),
  saveCode: (sessionId: string, code: string) =>
    api.patch(`/sessions/${sessionId}/code`, { code }).then((r) => r.data),
  checkStep: (sessionId: string, code: string) =>
    api.post(`/sessions/${sessionId}/check-step`, { code }).then((r) => r.data),
  getHint: (sessionId: string, code: string) =>
    api.post(`/sessions/${sessionId}/hint`, { code }).then((r) => r.data),
  runTests: (taskId: string, code: string) =>
    api.post(`/sessions/run-tests/${taskId}`, { code }).then((r) => r.data),
  freeRun: (taskId: string, code: string, stdin: string): Promise<{ output: string; error: string | null }> =>
    api.post(`/sessions/run/${taskId}`, { code, stdin }).then((r) => r.data),
  explainErrors: (taskId: string, code: string, errors: string[]) =>
    api.post(`/sessions/run-tests/${taskId}/explain`, { code, errors }).then((r) => r.data),
  startNew: (taskId: string, code?: string) =>
    api.post('/sessions', { task_id: taskId, force_new: true, code }).then((r) => r.data),
  /** "Write another solution" following one of the offered approaches (from the starter code). */
  startApproach: (taskId: string, approach: string) =>
    api.post('/sessions', { task_id: taskId, force_new: true, approach }).then((r) => r.data),
}

// Subjects (предмети) and AI practice
export const subjectsApi = {
  list: () => api.get('/subjects').then((r) => r.data),
  get: (id: string) => api.get(`/subjects/${id}`).then((r) => r.data),
  practice: (id: string, data: { language: string; level: string; topic: string }): Promise<{ task_id: string; title: string }> =>
    api.post(`/subjects/${id}/practice`, data, { timeout: 300_000 }).then((r) => r.data),
  deletePractice: (taskId: string) => api.delete(`/practice/${taskId}`),
  create: (data: object) => api.post('/admin/subjects', data).then((r) => r.data),
  update: (id: string, data: object) => api.put(`/admin/subjects/${id}`, data).then((r) => r.data),
  remove: (id: string) => api.delete(`/admin/subjects/${id}`),
  studentPractice: (id: string) => api.get(`/subjects/${id}/student-practice`).then((r) => r.data),
  practiceWork: (taskId: string) => api.get(`/practice/${taskId}/work`).then((r) => r.data),
}

// A student's electives (chosen once; then changes go to the admin as requests)
export const electivesApi = {
  mine: () => api.get('/me/electives').then((r) => r.data),
  choose: (subject_id: string, semester: number, reason = '') => api.post('/me/electives', { subject_id, semester, reason }).then((r) => r.data),
  drop: (subject_id: string, reason = '') => api.delete(`/me/electives/${subject_id}`, { params: { reason } }).then((r) => r.data),
  confirm: () => api.post('/me/electives/confirm').then((r) => r.data),
  request: (data: { remove_subject_id?: string | null; add_subject_id?: string | null; add_semester?: number | null; reason: string }) =>
    api.post('/me/elective-requests', data).then((r) => r.data),
  cancel: (id: string) => api.delete(`/me/elective-requests/${id}`),
  adminList: (status = 'pending') => api.get('/admin/elective-requests', { params: { status } }).then((r) => r.data),
  approve: (id: string, note: string) => api.post(`/admin/elective-requests/${id}/approve`, { note }).then((r) => r.data),
  reject: (id: string, note: string) => api.post(`/admin/elective-requests/${id}/reject`, { note }).then((r) => r.data),
  reopen: (userId: string) => api.post(`/admin/users/${userId}/electives/reopen`).then((r) => r.data),
}

// A person's own AI key (students too)
export const ownKeyApi = {
  get: () => api.get('/me/ai-key').then((r) => r.data),
  test: (data: object) => api.post('/me/ai-key/test', data).then((r) => r.data),
  save: (data: object) => api.put('/me/ai-key', data).then((r) => r.data),
  remove: () => api.delete('/me/ai-key').then((r) => r.data),
  reveal: (): Promise<string> => api.post('/me/ai-key/reveal').then((r) => r.data.api_key),
}

// Courses, assignments, submissions
export const coursesApi = {
  mine: () => api.get('/courses').then((r) => r.data),
  create: (data: object) => api.post('/courses', data).then((r) => r.data),
  adminList: () => api.get('/admin/courses').then((r) => r.data),
  remove: (id: string) => api.delete(`/courses/${id}`),
  join: (code: string) => api.post('/courses/join', { code }).then((r) => r.data),
  get: (id: string) => api.get(`/courses/${id}`).then((r) => r.data),
  update: (id: string, data: object) => api.patch(`/courses/${id}`, data).then((r) => r.data),
  newJoinCode: (id: string) => api.post(`/courses/${id}/join-code`).then((r) => r.data),
  addGroup: (id: string, name: string, language: 'mk' | 'en' | null = null) =>
    api.post(`/courses/${id}/groups`, { name, language }).then((r) => r.data),
  renameGroup: (id: string, gid: string, name: string, language?: 'mk' | 'en' | null) =>
    api.patch(`/courses/${id}/groups/${gid}`, language === undefined ? { name } : { name, language }).then((r) => r.data),
  deleteGroup: (id: string, gid: string) => api.delete(`/courses/${id}/groups/${gid}`),
  members: (id: string) => api.get(`/courses/${id}/members`).then((r) => r.data),
  addMembers: (id: string, data: object) => api.post(`/courses/${id}/members`, data).then((r) => r.data),
  updateMember: (id: string, uid: string, data: object) => api.patch(`/courses/${id}/members/${uid}`, data).then((r) => r.data),
  removeMember: (id: string, uid: string) => api.delete(`/courses/${id}/members/${uid}`),
  createAssignment: (id: string, data: object) => api.post(`/courses/${id}/assignments`, data).then((r) => r.data),
  gradebook: (id: string) => api.get(`/courses/${id}/gradebook`).then((r) => r.data),
  /** Downloads the CSV with the auth header (a plain link would not send the token). */
  downloadGradebook: async (id: string) => {
    const r = await api.get(`/courses/${id}/gradebook.csv`, { responseType: 'blob' })
    const name = /filename="([^"]+)"/.exec(r.headers['content-disposition'] || '')?.[1] || 'gradebook.csv'
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url; a.download = name; a.click()
    URL.revokeObjectURL(url)
  },
}

// Course e-mail (drafts → approval → sending), notices for students
export const mailApi = {
  list: (courseId: string) => api.get(`/courses/${courseId}/emails`).then((r) => r.data),
  create: (courseId: string, data: object) => api.post(`/courses/${courseId}/emails`, data).then((r) => r.data),
  get: (id: string) => api.get(`/emails/${id}`).then((r) => r.data),
  update: (id: string, data: object) => api.put(`/emails/${id}`, data).then((r) => r.data),
  improve: (id: string, notes: string) => api.post(`/emails/${id}/ai`, { notes }).then((r) => r.data),
  send: (id: string) => api.post(`/emails/${id}/send`).then((r) => r.data),
  cancel: (id: string) => api.post(`/emails/${id}/cancel`).then((r) => r.data),
  announcements: (courseId: string) => api.get(`/courses/${courseId}/announcements`).then((r) => r.data),
  adminStatus: () => api.get('/admin/mail').then((r) => r.data),
  adminTest: (to: string) => api.post('/admin/mail/test', { to }).then((r) => r.data),
  runReminders: () => api.post('/admin/reminders/run').then((r) => r.data),
}

// Lectures, exercises and other files of a course
export const materialsApi = {
  list: (courseId: string) => api.get(`/courses/${courseId}/materials`).then((r) => r.data),
  upload: (courseId: string, file: File, meta: { title: string; section: string; week: number | null; published: boolean },
    onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file); form.append('title', meta.title); form.append('section', meta.section)
    form.append('published', String(meta.published))
    if (meta.week != null) form.append('week', String(meta.week))
    return api.post(`/courses/${courseId}/materials`, form, {
      onUploadProgress: (e) => onProgress && e.total && onProgress(Math.round((e.loaded / e.total) * 100)),
    }).then((r) => r.data)
  },
  update: (id: string, data: object) => api.patch(`/materials/${id}`, data).then((r) => r.data),
  remove: (id: string) => api.delete(`/materials/${id}`),
  download: (id: string, name: string) => saveBlob(`/materials/${id}/file`, name),
  viewUrl: async (id: string) => {
    const r = await api.get(`/materials/${id}/view`, { responseType: 'blob' })
    return URL.createObjectURL(r.data)
  },
}

// Grading scheme, standing, the Excel grade sheet
export const standingApi = {
  scheme: (courseId: string) => api.get(`/courses/${courseId}/grading`).then((r) => r.data),
  saveScheme: (courseId: string, data: object) => api.put(`/courses/${courseId}/grading`, data).then((r) => r.data),
  standing: (courseId: string) => api.get(`/courses/${courseId}/standing`).then((r) => r.data),
  setFinal: (courseId: string, user_id: string, grade: number | null) =>
    api.put(`/courses/${courseId}/final-grades`, { user_id, grade }).then((r) => r.data),
  downloadSheet: async (courseId: string, group?: string) => {
    const r = await api.get(`/courses/${courseId}/gradesheet.xlsx`, { params: group ? { group } : {}, responseType: 'blob' })
    const name = /filename="([^"]+)"/.exec(r.headers['content-disposition'] || '')?.[1] || 'grades.xlsx'
    const href = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = href; a.download = name; a.click()
    setTimeout(() => URL.revokeObjectURL(href), 10_000)
  },
}

export const assignmentsApi = {
  get: (id: string) => api.get(`/assignments/${id}`).then((r) => r.data),
  update: (id: string, data: object) => api.put(`/assignments/${id}`, data).then((r) => r.data),
  remove: (id: string) => api.delete(`/assignments/${id}`),
  /** `uploadId`: diagram tasks — the picture the diagram was read from, handed in with it. */
  submit: (id: string, taskId: string, code: string, uploadId?: string | null) =>
    api.post(`/assignments/${id}/tasks/${taskId}/submit`, { code, upload_id: uploadId || null }).then((r) => r.data),
  /** A queued submission's result (status "pending" until it has been tested). */
  result: (submissionId: string) => api.get(`/submissions/${submissionId}/result`).then((r) => r.data),
  submissions: (id: string, params: { task_id?: string; user_id?: string } = {}) =>
    api.get(`/assignments/${id}/submissions`, { params }).then((r) => r.data),
  // exams
  start: (id: string) => api.post(`/assignments/${id}/start`).then((r) => r.data),
  finish: (id: string) => api.post(`/assignments/${id}/finish`).then((r) => r.data),
  /** Exam signals; never blocks or fails the page. */
  event: (id: string, kind: 'blur' | 'focus' | 'paste', task_id?: string, detail = '') =>
    api.post(`/assignments/${id}/events`, { kind, task_id, detail }).catch(() => undefined),
  // grading
  overview: (id: string) => api.get(`/assignments/${id}/overview`).then((r) => r.data),
  review: (id: string, user_id: string, task_id: string) =>
    api.get(`/assignments/${id}/review`, { params: { user_id, task_id } }).then((r) => r.data),
  setGrade: (id: string, data: { user_id: string; task_id: string; adjust: number; override: number | null; comment: string;
    rubric_scores?: Record<string, number> | null }) => api.put(`/assignments/${id}/grades`, data).then((r) => r.data),
  addComment: (submissionId: string, line: number, body: string, path = '') =>
    api.post(`/submissions/${submissionId}/comments`, { line, body, path }).then((r) => r.data),
  // file work (documents, projects)
  upload: (id: string, taskId: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData(); form.append('file', file)
    return api.post(`/assignments/${id}/tasks/${taskId}/upload`, form, {
      onUploadProgress: (e) => onProgress && e.total && onProgress(Math.round((e.loaded / e.total) * 100)),
    }).then((r) => r.data)
  },
  myUploads: (id: string, taskId: string) => api.get(`/assignments/${id}/tasks/${taskId}/uploads`).then((r) => r.data),
  download: (submissionId: string, name: string) => saveBlob(`/submissions/${submissionId}/download`, name),
  /** The file as a local blob: URL (for showing a PDF or picture in the page). */
  fileUrl: async (submissionId: string) => {
    const r = await api.get(`/submissions/${submissionId}/download`, { params: { inline: true }, responseType: 'blob' })
    return URL.createObjectURL(r.data)
  },
  tree: (submissionId: string) => api.get(`/submissions/${submissionId}/tree`).then((r) => r.data),
  entry: (submissionId: string, path: string) => api.get(`/submissions/${submissionId}/entry`, { params: { path } }).then((r) => r.data),
  setAttendance: (id: string, user_id: string, status: string | null) =>
    api.put(`/assignments/${id}/attendance`, { user_id, status }).then((r) => r.data),
  deleteComment: (commentId: string) => api.delete(`/comments/${commentId}`),
  publish: (id: string, published: boolean) => api.post(`/assignments/${id}/publish`, { published }).then((r) => r.data),
  gradingAssist: (id: string, user_id: string, task_id: string): Promise<GradingSuggestion> =>
    api.post(`/assignments/${id}/grading-assist`, { user_id, task_id }).then((r) => r.data),
  taskBank: (courseId: string) => api.get(`/courses/${courseId}/task-bank`).then((r) => r.data),
  generateTasks: (courseId: string, data: { language: string; level: string; topic: string; count: number; type: 'tests' | 'project' }) =>
    api.post(`/courses/${courseId}/generate-tasks`, data, { timeout: 900_000 }).then((r) => r.data),
  feedback: (id: string, task_id: string) => api.get(`/assignments/${id}/feedback`, { params: { task_id } }).then((r) => r.data),
  similarity: (id: string, threshold: number) => api.get(`/assignments/${id}/similarity`, { params: { threshold } }).then((r) => r.data),
  submission: (submissionId: string) => api.get(`/submissions/${submissionId}`).then((r) => r.data),
}

export const profileApi = {
  mine: () => api.get('/profile').then((r) => r.data),
  update: (data: object) => api.put('/profile', data).then((r) => r.data),
  uploadAvatar: (blob: Blob) => {
    const form = new FormData()
    form.append('file', blob, 'avatar.jpg')
    return api.put('/profile/avatar', form).then((r) => r.data)
  },
  removeAvatar: () => api.delete('/profile/avatar'),
  changePassword: (current: string, next: string) => api.post('/profile/password', { current, new: next }),
  of: (userId: string) => api.get(`/users/${userId}/profile`).then((r) => r.data),
}

export const usersApi = {
  list: (params: { q?: string; role?: string }) => api.get('/admin/users', { params }).then((r) => r.data),
  setRole: (id: string, role: string) => api.patch(`/admin/users/${id}`, { role }).then((r) => r.data),
}

export const ssoApi = {
  config: (): Promise<{ enabled: boolean }> => api.get('/auth/microsoft/config').then((r) => r.data),
  /** Full-page redirect to Microsoft; it comes back to /auth/callback#token=... */
  loginUrl: () => `${API_BASE}/auth/microsoft/login`,
}

// Admin
/** Save a blob from an authenticated request as a file (the browser can't add the login token to a plain link). */
export async function saveBlob(url: string, name: string) {
  const r = await api.get(url, { responseType: 'blob' })
  const href = URL.createObjectURL(r.data)
  const link = document.createElement('a')
  link.href = href; link.download = name; link.click()
  setTimeout(() => URL.revokeObjectURL(href), 10_000)
}

export const adminApi = {
  translate: (data: { title: string; description: string; source: 'mk' | 'en'; target: 'mk' | 'en' }): Promise<{ title: string; description: string }> =>
    api.post('/admin/tasks/translate', data).then((r) => r.data),
  uploadReference: (taskId: string, file: File) => {
    const form = new FormData(); form.append('file', file)
    return api.put(`/admin/tasks/${taskId}/reference`, form).then((r) => r.data)
  },
  deleteReference: (taskId: string) => api.delete(`/admin/tasks/${taskId}/reference`),
  downloadReference: (taskId: string, name: string) => saveBlob(`/admin/tasks/${taskId}/reference`, name),
  listTasks: () => api.get('/admin/tasks').then((r) => r.data),
  getTask: (id: string) => api.get(`/admin/tasks/${id}`).then((r) => r.data),
  createTask: (data: object) => api.post('/admin/tasks', data).then((r) => r.data),
  updateTask: (id: string, data: object) => api.put(`/admin/tasks/${id}`, data).then((r) => r.data),
  deleteTask: (id: string) => api.delete(`/admin/tasks/${id}`),
  taskUsage: (id: string): Promise<{ sessions: number; students: number }> =>
    api.get(`/admin/tasks/${id}/usage`).then((r) => r.data),
  /** Languages the code runner has installed. */
  languages: (): Promise<{ languages: string[]; runner: boolean }> => api.get('/admin/languages').then((r) => r.data),
  /** Run code (the model solution) on tests from the form — used to fill in expected outputs. */
  runPreview: (language: string, code: string, test_cases: object[]):
    Promise<{ results: { actual_output: string; error: string | null; passed: boolean }[] }> =>
    api.post('/admin/run-preview', { language, code, test_cases }).then((r) => r.data),
  /** Diagrams: AI draws the model solution from the task text / a PDF or picture of the task; tests made from it. */
  diagramDraft: (d: { kind: string; description: string; lang: string; file?: File | null }):
    Promise<{ model_solution: string; tests: { type: string; test_code: string; expected_output: string; is_hidden: boolean }[]; used_file: boolean }> => {
    const form = new FormData()
    form.append('kind', d.kind); form.append('description', d.description); form.append('lang', d.lang)
    if (d.file) form.append('file', d.file)
    return api.post('/admin/tasks/diagram-draft', form).then((r) => r.data)
  },
  diagramTests: (d: { kind: string; model_solution: string; lang: string }):
    Promise<{ tests: { type: string; test_code: string; expected_output: string; is_hidden: boolean }[] }> =>
    api.post('/admin/tasks/diagram-tests', d).then((r) => r.data),
  /** AI drafts new tests from the description + model solution; each is already run on the model solution. */
  suggestTests: (data: { language: string; description: string; model_solution: string; test_cases: object[]; count?: number }):
    Promise<{ tests: { title: string; type: 'code_sample' | 'stdin_stdout'; test_code: string; stdin: string; expected_output: string;
      is_hidden: boolean; checked: boolean | null; error?: string }[] }> =>
    api.post('/admin/tasks/suggest-tests', data).then((r) => r.data),
  updateTestCase: (taskId: string, tcId: string, data: object) =>
    api.put(`/admin/tasks/${taskId}/test-cases/${tcId}`, data).then((r) => r.data),
  addTestCase: (taskId: string, data: object) =>
    api.post(`/admin/tasks/${taskId}/test-cases`, data).then((r) => r.data),
  importPreview: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post('/admin/import/coderunner/preview', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data)
  },
  getAISettings: () => api.get('/admin/ai-settings').then((r) => r.data),
  saveAISettings: (data: object) => api.put('/admin/ai-settings', data).then((r) => r.data),
  testAISettings: (data: object) => api.post('/admin/ai-settings/test', data).then((r) => r.data),
  resetAISettings: () => api.delete('/admin/ai-settings').then((r) => r.data),
  revealAIKey: (): Promise<string> => api.post('/admin/ai-settings/reveal').then((r) => r.data.api_key),
  monitoring: (range: string) => api.get('/admin/monitoring', { params: { range } }).then((r) => r.data),
  importCommit: (tasks: object[], subject_id: string | null = null) => api.post('/admin/import/commit', { tasks, subject_id }).then((r) => r.data),
  deleteTestCase: (taskId: string, tcId: string) =>
    api.delete(`/admin/tasks/${taskId}/test-cases/${tcId}`),
}

/** LTI 1.3: ALE inside the faculty's Moodle (courses.finki). */
export const ltiApi = {
  setupInfo: (s: string) => api.get('/lti/setup', { params: { s } }).then((r) => r.data),
  setup: (s: string, course_id: string | null) => api.post('/lti/setup', { s, course_id }).then((r) => r.data),
  deeplinkInfo: (d: string) => api.get('/lti/deeplink', { params: { d } }).then((r) => r.data),
  deeplink: (d: string, assignment_ids: string[], course_link: boolean) =>
    api.post('/lti/deeplink', { d, assignment_ids, course_link }).then((r) => r.data),
  course: (courseId: string) => api.get(`/courses/${courseId}/lti`).then((r) => r.data),
  roster: (courseId: string) => api.post(`/courses/${courseId}/lti/roster`).then((r) => r.data),
  grades: (courseId: string, assignment_id: string | null = null) => api.post(`/courses/${courseId}/lti/grades`, { assignment_id }).then((r) => r.data),
  unlink: (courseId: string, ctxId: string) => api.delete(`/courses/${courseId}/lti/${ctxId}`),
  admin: () => api.get('/admin/lti').then((r) => r.data),
  addPlatform: (data: object) => api.post('/admin/lti/platforms', data).then((r) => r.data),
  updatePlatform: (id: string, data: object) => api.put(`/admin/lti/platforms/${id}`, data).then((r) => r.data),
  deletePlatform: (id: string) => api.delete(`/admin/lti/platforms/${id}`),
  newRegistration: (name: string) => api.post('/admin/lti/registrations', { name }).then((r) => r.data),
}

// Logs: AI calls, test runs and what people do
export type LogParams = Record<string, string | number | boolean | undefined>
const clean = (p: LogParams) => Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined && v !== ''))
export const logsApi = {
  admin: (p: LogParams) => api.get('/admin/logs', { params: clean(p) }).then((r) => r.data),
  course: (courseId: string, p: LogParams) => api.get(`/courses/${courseId}/logs`, { params: clean(p) }).then((r) => r.data),
  mine: (p: LogParams) => api.get('/me/activity', { params: clean(p) }).then((r) => r.data),
  csv: async (p: LogParams) => {
    const r = await api.get('/admin/logs.csv', { params: clean(p), responseType: 'blob' })
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url; a.download = `ale-logs-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.csv`; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}
