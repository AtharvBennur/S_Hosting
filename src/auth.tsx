import React, { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

export const normalizeApiBase = (base?: string) => {
  if (!base) return '';
  const trimmed = base.trim();
  const cleaned = trimmed.replace(/\/+$/, '');
  if (
    cleaned === '0.0.0.0' ||
    cleaned.startsWith('0.0.0.0:') ||
    cleaned.includes('://0.0.0.0') ||
    cleaned === 'http://0.0.0.0' ||
    cleaned === 'https://0.0.0.0' ||
    cleaned === 'localhost' ||
    cleaned.startsWith('localhost:')
  ) {
    return '';
  }
  return cleaned;
};

export const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE);
export type Role = 'MINISTRY' | 'STATE_NODAL_AUTHORITY' | 'DISTRICT_AUTHORITY' | 'MEMBER_OF_PARLIAMENT';
export type User = {
  id: number; name: string; email: string; identity_id: string; role: Role; status: string;
  scope_type: string; scope_id?: string; permissions: string[];
};
type AuthContextValue = { user: User | null; loading: boolean; demoEnvironment: boolean; login: (payload: Record<string, string>) => Promise<void>; logout: () => Promise<void>; can: (permission: string) => boolean };
const AuthContext = createContext<AuthContextValue | null>(null);

axios.interceptors.request.use(config => {
  const token = localStorage.getItem('mplads_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [demoEnvironment, setDemoEnvironment] = useState(false);
  useEffect(() => {
    const token = localStorage.getItem('mplads_access_token');
    if (!token) { setLoading(false); return; }
    axios.get(`${API_BASE}/api/auth/me`).then(response => setUser(response.data)).catch(() => localStorage.removeItem('mplads_access_token')).finally(() => setLoading(false));
  }, []);
  const login = async (payload: Record<string, string>) => {
    const response = await axios.post(`${API_BASE}/api/auth/login`, payload);
    localStorage.setItem('mplads_access_token', response.data.access_token);
    setUser(response.data.user);
    setDemoEnvironment(Boolean(response.data.demo_environment));
  };
  const logout = async () => {
    try { await axios.post(`${API_BASE}/api/auth/logout`); } finally { localStorage.removeItem('mplads_access_token'); setUser(null); }
  };
  const value = useMemo(() => ({ user, loading, demoEnvironment, login, logout, can: (permission: string) => Boolean(user?.permissions.includes(permission)) }), [user, loading, demoEnvironment]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
