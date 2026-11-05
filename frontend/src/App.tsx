import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { useLanguage } from './i18n/LanguageContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import SubjectPage from './pages/SubjectPage'
import TaskPage from './pages/TaskPage'
import AdminTaskListPage from './pages/admin/AdminTaskListPage'
import AdminTaskFormPage from './pages/admin/AdminTaskFormPage'
import AdminImportPage from './pages/admin/AdminImportPage'
import AdminAISettingsPage from './pages/admin/AdminAISettingsPage'
import AdminMonitoringPage from './pages/admin/AdminMonitoringPage'
import AdminMailPage from './pages/admin/AdminMailPage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import CoursesPage from './pages/CoursesPage'
import CoursePage from './pages/CoursePage'
import AssignmentPage from './pages/AssignmentPage'
import TestsPage from './pages/TestsPage'
import ProfilePage from './pages/ProfilePage'
import UserProfilePage from './pages/UserProfilePage'
import QuickEntryPage from './pages/QuickEntryPage'
import WorkPage from './pages/WorkPage'
import GradingPage from './pages/GradingPage'
import SimilarityPage from './pages/SimilarityPage'
import AssignmentFormPage from './pages/AssignmentFormPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import { isStaff } from './types'
import { TourProvider } from './components/Tour'
import LtiPage from './pages/LtiPage'
import AdminLtiPage from './pages/admin/AdminLtiPage'
import AdminCoursesPage from './pages/admin/AdminCoursesPage'
import AdminElectivesPage from './pages/admin/AdminElectivesPage'

/** adminOnly: admins; staffOnly: assistants, professors and admins (task authors). */
function ProtectedRoute({ children, adminOnly = false, staffOnly = false }: { children: React.ReactNode; adminOnly?: boolean; staffOnly?: boolean }) {
  const { user, loading } = useAuth()
  const { t } = useLanguage()
  if (loading) return <div className="flex items-center justify-center h-screen text-ink-muted">{t('common.loading')}</div>
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/courses" replace />
  if (staffOnly && !isStaff(user)) return <Navigate to="/courses" replace />
  return <>{children}</>
}

export default function App() {
  const { user, loading } = useAuth()
  const { t } = useLanguage()
  if (loading) return <div className="flex items-center justify-center h-screen text-ink-muted">{t('common.loading')}</div>

  return (
    <TourProvider>
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/courses" replace /> : <LoginPage />} />
      <Route path="/register" element={user ? <Navigate to="/courses" replace /> : <RegisterPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/lti" element={<LtiPage />} />
      <Route path="/courses" element={<ProtectedRoute><CoursesPage /></ProtectedRoute>} />
      <Route path="/courses/:courseId" element={<ProtectedRoute><CoursePage /></ProtectedRoute>} />
      <Route path="/courses/:courseId/assignments/new" element={<ProtectedRoute><AssignmentFormPage /></ProtectedRoute>} />
      <Route path="/assignments/:assignmentId" element={<ProtectedRoute><AssignmentPage /></ProtectedRoute>} />
      <Route path="/assignments/:assignmentId/edit" element={<ProtectedRoute><AssignmentFormPage /></ProtectedRoute>} />
      <Route path="/assignments/:assignmentId/grading" element={<ProtectedRoute><GradingPage /></ProtectedRoute>} />
      <Route path="/assignments/:assignmentId/similarity" element={<ProtectedRoute><SimilarityPage /></ProtectedRoute>} />
      <Route path="/assignments/:assignmentId/quick" element={<ProtectedRoute><QuickEntryPage /></ProtectedRoute>} />
      <Route path="/assignments/:assignmentId/work/:taskId" element={<ProtectedRoute><WorkPage /></ProtectedRoute>} />
      <Route path="/tasks" element={<Navigate to="/courses" replace />} />
      <Route path="/subjects/:subjectId" element={<ProtectedRoute><SubjectPage /></ProtectedRoute>} />
      <Route path="/tasks/:taskId" element={<ProtectedRoute><TaskPage /></ProtectedRoute>} />
      <Route path="/tasks/:taskId/tests" element={<ProtectedRoute><TestsPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="/users/:userId" element={<ProtectedRoute><UserProfilePage /></ProtectedRoute>} />
      <Route path="/admin/tasks" element={<ProtectedRoute staffOnly><AdminTaskListPage /></ProtectedRoute>} />
      <Route path="/admin/users" element={<ProtectedRoute adminOnly><AdminUsersPage /></ProtectedRoute>} />
      <Route path="/admin/ai" element={<ProtectedRoute adminOnly><AdminAISettingsPage /></ProtectedRoute>} />
      <Route path="/admin/monitoring" element={<ProtectedRoute adminOnly><AdminMonitoringPage /></ProtectedRoute>} />
 <Route path="/admin/courses" element={<ProtectedRoute adminOnly><AdminCoursesPage /></ProtectedRoute>} />
 <Route path="/admin/electives" element={<ProtectedRoute adminOnly><AdminElectivesPage /></ProtectedRoute>} />
      <Route path="/admin/lti" element={<ProtectedRoute adminOnly><AdminLtiPage /></ProtectedRoute>} />
      <Route path="/admin/mail" element={<ProtectedRoute adminOnly><AdminMailPage /></ProtectedRoute>} />
      <Route path="/admin/tasks/import" element={<ProtectedRoute staffOnly><AdminImportPage /></ProtectedRoute>} />
      <Route path="/admin/tasks/new" element={<ProtectedRoute staffOnly><AdminTaskFormPage /></ProtectedRoute>} />
      <Route path="/admin/tasks/:taskId/edit" element={<ProtectedRoute staffOnly><AdminTaskFormPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to={user ? '/courses' : '/login'} replace />} />
    </Routes>
    </TourProvider>
  )
}
