import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { adminApi } from '../../services/api'
import { useAuth } from '../../contexts/AuthContext'
import { TaskListItem } from '../../types'
import { Plus, Edit2, Trash2, ArrowLeft, Code2, LogOut } from 'lucide-react'

export default function AdminTaskListPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: tasks = [], isLoading } = useQuery<TaskListItem[]>({
    queryKey: ['admin-tasks'],
    queryFn: adminApi.listTasks,
  })

  const deleteTask = useMutation({
    mutationFn: (id: string) => adminApi.deleteTask(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-tasks'] }),
  })

  const handleDelete = (id: string, title: string) => {
    if (confirm(`Delete task "${title}"? This cannot be undone.`)) {
      deleteTask.mutate(id)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Code2 className="text-blue-600" size={22} />
          <span className="font-bold text-gray-900">ALE Admin</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <Link to="/tasks" className="btn-secondary text-sm py-1.5 px-3">
            <ArrowLeft size={14} /> Student View
          </Link>
          <button onClick={() => { logout(); navigate('/login') }} className="btn-secondary text-sm py-1.5 px-3">
            <LogOut size={14} />
          </button>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Manage Tasks</h1>
          <Link to="/admin/tasks/new" className="btn-primary">
            <Plus size={16} /> New Task
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-4 animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="card p-10 text-center text-gray-400">
            No tasks yet. <Link to="/admin/tasks/new" className="text-blue-600 hover:underline">Create one.</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div key={task.id} className="card p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{task.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded uppercase">
                      {task.language}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(task.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/admin/tasks/${task.id}/edit`}
                    className="btn-secondary py-1.5 px-3 text-sm"
                  >
                    <Edit2 size={13} /> Edit
                  </Link>
                  <button
                    onClick={() => handleDelete(task.id, task.title)}
                    className="btn-danger py-1.5 px-3 text-sm"
                    disabled={deleteTask.isPending}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
