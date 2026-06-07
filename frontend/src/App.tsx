import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import TaskListPage from './pages/TaskListPage'
import TaskPage from './pages/TaskPage'
import AdminTaskListPage from './pages/admin/AdminTaskListPage'
import AdminTaskFormPage from './pages/admin/AdminTaskFormPage'

function ProtectedRoute({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/tasks" replace />
  return <>{children}</>
}

export default function App() {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-gray-500">Loading...</div>

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/tasks" replace /> : <LoginPage />} />
      <Route path="/register" element={user ? <Navigate to="/tasks" replace /> : <RegisterPage />} />
      <Route path="/tasks" element={<ProtectedRoute><TaskListPage /></ProtectedRoute>} />
      <Route path="/tasks/:taskId" element={<ProtectedRoute><TaskPage /></ProtectedRoute>} />
      <Route path="/admin/tasks" element={<ProtectedRoute adminOnly><AdminTaskListPage /></ProtectedRoute>} />
      <Route path="/admin/tasks/new" element={<ProtectedRoute adminOnly><AdminTaskFormPage /></ProtectedRoute>} />
      <Route path="/admin/tasks/:taskId/edit" element={<ProtectedRoute adminOnly><AdminTaskFormPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to={user ? '/tasks' : '/login'} replace />} />
    </Routes>
  )
}
