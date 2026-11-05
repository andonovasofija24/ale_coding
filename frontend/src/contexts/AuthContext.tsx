import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from '../types'
import { authApi } from '../services/api'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  /** After Microsoft sign-in: store the token and load the account. */
  loginWithToken: (token: string) => Promise<void>
  /** Reload the account (after editing the profile or the picture). */
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('ale_user')
    const token = localStorage.getItem('ale_token')
    if (stored && token) {
      setUser(JSON.parse(stored))
      // Refresh in the background: an admin may have changed the role since the last sign-in.
      authApi.me().then((u: User) => {
        localStorage.setItem('ale_user', JSON.stringify(u))
        setUser(u)
      }).catch(() => { /* 401 is handled by the API client */ })
    }
    setLoading(false)
  }, [])

  const loginWithToken = async (token: string) => {
    localStorage.setItem('ale_token', token)
    const u: User = await authApi.me()
    localStorage.setItem('ale_user', JSON.stringify(u))
    setUser(u)
  }

  const login = async (email: string, password: string) => {
    const data = await authApi.login({ email, password })
    localStorage.setItem('ale_token', data.access_token)
    localStorage.setItem('ale_user', JSON.stringify(data.user))
    setUser(data.user)
  }

  const register = async (email: string, password: string, name: string) => {
    const data = await authApi.register({ email, password, name })
    localStorage.setItem('ale_token', data.access_token)
    localStorage.setItem('ale_user', JSON.stringify(data.user))
    setUser(data.user)
  }

  const refreshUser = async () => {
    const u: User = await authApi.me()
    localStorage.setItem('ale_user', JSON.stringify(u))
    setUser(u)
  }

  const logout = () => {
    localStorage.removeItem('ale_token')
    localStorage.removeItem('ale_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, loginWithToken, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
