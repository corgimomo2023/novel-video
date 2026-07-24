import { Film, Gauge, LayoutDashboard, ListVideo, LogOut, Menu, Settings, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const nav = [
  { to: '/', label: '總覽', icon: LayoutDashboard }, { to: '/projects', label: '作品', icon: Film },
  { to: '/jobs', label: '生成隊列', icon: ListVideo }, { to: '/gpu', label: 'GPU運算', icon: Gauge },
  { to: '/settings', label: '設定', icon: Settings },
]

export function AppLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const sidebar = <>
    <div className="flex h-16 items-center gap-3 border-b px-5"><div className="grid h-9 w-9 place-items-center rounded-lg bg-blue-600 text-white"><Film size={20}/></div><div><p className="text-sm font-bold">小說影片工作室</p><p className="text-[11px] text-slate-500">AI VIDEO PIPELINE</p></div></div>
    <nav aria-label="主要功能" className="admin-module-nav flex-1 space-y-1 p-3">{nav.map(item => <NavLink key={item.to} to={item.to} end={item.to === '/'} onClick={() => setOpen(false)} className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}><item.icon size={18}/>{item.label}</NavLink>)}</nav>
    <div className="border-t p-3"><div className="mb-2 px-3 text-xs text-slate-500">登入：{user}</div><button className="nav-link w-full" onClick={() => void logout()}><LogOut size={18}/>登出</button></div>
  </>
  return <div className="min-h-screen bg-slate-50"><aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r bg-white lg:flex">{sidebar}</aside>
    {open && <div className="fixed inset-0 z-40 bg-slate-950/30 lg:hidden" onClick={() => setOpen(false)}><aside className="flex h-full w-72 flex-col bg-white" onClick={e => e.stopPropagation()}>{sidebar}</aside></div>}
    <main className="lg:pl-64"><header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-white/95 px-4 backdrop-blur sm:px-7"><button className="btn-secondary p-2 lg:hidden" onClick={() => setOpen(!open)}>{open ? <X size={18}/> : <Menu size={18}/>}</button><div className="ml-auto flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-500"/><span className="text-xs font-medium text-slate-500">系統正常</span></div></header><div className="mx-auto max-w-[1500px] p-4 sm:p-7">{children}</div></main></div>
}
