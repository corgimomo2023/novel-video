import { Film } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'

export function LoginPage() {
  const { login } = useAuth(); const [username, setUsername] = useState('alan'); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); try { await login(username, password) } catch (err) { setError(err instanceof Error ? err.message : '登入失敗') } finally { setBusy(false) } }
  return <main className="grid min-h-screen place-items-center bg-slate-100 p-4"><div className="w-full max-w-md"><div className="mb-6 text-center"><div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-xl bg-blue-600 text-white"><Film/></div><h1 className="text-2xl font-bold">小說影片工作室</h1><p className="mt-1 text-sm text-slate-500">管理分鏡、GPU任務及影片輸出</p></div><form onSubmit={e => void submit(e)} className="card space-y-4 p-6"><div><label className="label">帳戶</label><input className="field" value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" required/></div><div><label className="label">密碼</label><input className="field" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required/></div>{error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button className="btn-primary w-full" disabled={busy}>{busy ? '登入中…' : '登入工作室'}</button></form></div></main>
}
