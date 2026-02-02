import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { loginAPI, getMeAPI } from '@/services/auth.service'
import { getToken, setToken, removeToken } from '@/utils/token'
import type { User } from '@/types/auth.types'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = getToken()
      if (token) {
        try {
          const userData = await getMeAPI()
          setUser(userData)
        } catch (error) {
          removeToken()
        }
      }
      setLoading(false)
    }
    initAuth()
  }, [])

  const login = async (username: string, password: string) => {
    const { access_token } = await loginAPI({ username, password })
    setToken(access_token)
    const userData = await getMeAPI()
    setUser(userData)
  }

  const logout = () => {
    removeToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
