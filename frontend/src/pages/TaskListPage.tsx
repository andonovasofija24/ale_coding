import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { tasksApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { TaskListItem } from '../types'
import { Code2, LogOut, Settings, BookOpen } from 'lucide-react'

export default function TaskListPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const { data: tasks = [], isLoading } = useQuery<TaskListItem[]>({
    queryKey: ['tasks'],
    queryFn: tasksApi.list,
  })

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Code2 className="text-blue-600" size={22} />
          <span className="font-bold text-gray-900">ALE</span>
          <span className="text-gray-400 text-sm ml-1">Adaptive Learning Environment</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user?.name}</span>
          {user?.role === 'admin' && (
            <Link to="/admin/tasks" className="btn-secondary text-sm py-1.5 px-3">
              <Settings size={14} /> Admin
            </Link>
          )}
          <button onClick={handleLogout} className="btn-secondary text-sm py-1.5 px-3">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center gap-2 mb-6">
          <BookOpen className="text-blue-600" size={22} />
          <h1 className="text-2xl font-bold">Programming Tasks</h1>
        </div>

        {isLoading ? (
          <div className="grid gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-5 animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-1/3 mb-2" />
                <div className="h-4 bg-gray-100 rounded w-1/4" />
              </div>
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="card p-10 text-center text-gray-400">
            <BookOpen size={40} className="mx-auto mb-3 opacity-40" />
            <p>No tasks available yet.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {tasks.map((task) => (
              <Link
                key={task.id}
                to={`/tasks/${task.id}`}
                className="card p-5 hover:border-blue-300 hover:shadow-md transition-all group"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                      {task.title}
                    </h2>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium uppercase">
                        {task.language}
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(task.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <span className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity text-sm">
                    Open →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
