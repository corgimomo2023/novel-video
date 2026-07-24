import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../lib/api'

type AuthContextValue = { user: string | null; loading: boolean; login: (username: string, password: string) => Promise<void>; logout: () => Promise<void> }
const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => { api<{ username: string }>('/api/auth/me').then(x => setUser(x.username)).catch(() => setUser(null)).finally(() => setLoading(false)) }, [])
  const login = useCallback(async (username: string, password: string) => {
    const result = await api<{ username: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) })
    setUser(result.username)
  }, [])
  const logout = useCallback(async () => { await api('/api/auth/logout', { method: 'POST' }); setUser(null) }, [])
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth requires AuthProvider')
  return value
}
