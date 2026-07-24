import { CheckCircle2, Clock3, Film, Layers3 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader, LoadingScreen } from '../components/Page'
import { StatusBadge } from '../components/StatusBadge'
import { api, formatDate } from '../lib/api'
import type { DashboardData } from '../types'

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  useEffect(() => { const load = () => api<DashboardData>('/api/dashboard').then(setData); void load(); const timer = setInterval(load, 3000); return () => clearInterval(timer) }, [])
  if (!data) return <LoadingScreen/>
  const stats = [{label:'作品',value:data.projects,icon:Film,tone:'bg-blue-50 text-blue-700'}, {label:'分鏡',value:data.shots,icon:Layers3,tone:'bg-violet-50 text-violet-700'}, {label:'已完成',value:data.completed,icon:CheckCircle2,tone:'bg-emerald-50 text-emerald-700'}, {label:'處理中',value:data.queued,icon:Clock3,tone:'bg-amber-50 text-amber-700'}]
  return <><PageHeader title="製作總覽" description="由小說分鏡到GPU生成及最終輸出的統一控制台" action={<Link className="btn-primary" to="/projects">管理作品</Link>}/><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{stats.map(s => <div key={s.label} className="card p-5"><div className={`mb-4 grid h-10 w-10 place-items-center rounded-lg ${s.tone}`}><s.icon size={20}/></div><p className="text-3xl font-bold">{s.value}</p><p className="mt-1 text-sm text-slate-500">{s.label}</p></div>)}</div>
    <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_.6fr]"><section className="card overflow-hidden"><div className="border-b px-5 py-4"><h2 className="font-semibold">最近生成任務</h2></div>{data.recent_jobs.length ? <div className="divide-y">{data.recent_jobs.map(job => <div key={job.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center"><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{job.shot_title}</p><p className="mt-1 truncate text-xs text-slate-500">{job.project_title} · {job.engine} · {formatDate(job.created_at)}</p></div><StatusBadge status={job.status}/></div>)}</div> : <p className="p-8 text-center text-sm text-slate-500">未有生成任務</p>}</section>
      <aside className="card p-5"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">目前運算模式</p><div className="mt-4 rounded-xl bg-slate-950 p-5 text-white"><p className="text-sm font-semibold">Mock GPU Worker</p><p className="mt-2 text-xs leading-5 text-slate-300">完整測試排隊、處理及影片回傳流程，不會產生雲端GPU費用。</p><div className="mt-5 flex items-center gap-2 text-xs text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400"/>Ready</div></div><Link className="btn-secondary mt-4 w-full" to="/gpu">檢視GPU設定</Link></aside></div></>
}
