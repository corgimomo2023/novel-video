import { ArrowRight, Plus, Video } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { EmptyState, LoadingScreen, PageHeader } from '../components/Page'
import { api, formatDate } from '../lib/api'
import type { Project, ProjectSummary } from '../types'

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null); const [showForm, setShowForm] = useState(false); const [title, setTitle] = useState(''); const [source, setSource] = useState(''); const navigate = useNavigate()
  const load = () => api<ProjectSummary[]>('/api/projects').then(setProjects)
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) { event.preventDefault(); const project = await api<Project>('/api/projects', { method:'POST', body:JSON.stringify({title,source_text:source}) }); navigate(`/projects/${project.id}`) }
  if (!projects) return <LoadingScreen/>
  return <><PageHeader title="作品" description="管理小說來源、角色、分鏡及每集輸出" action={<button className="btn-primary" onClick={() => setShowForm(!showForm)}><Plus size={17}/>新增作品</button>}/>
    {showForm && <form onSubmit={e => void create(e)} className="card mb-6 grid gap-4 p-5 lg:grid-cols-[.6fr_1.4fr_auto] lg:items-end"><div><label className="label">作品名稱</label><input className="field" value={title} onChange={e=>setTitle(e.target.value)} placeholder="例如：第一集 雨夜重逢" required/></div><div><label className="label">小說原文</label><textarea className="field min-h-11 resize-y" value={source} onChange={e=>setSource(e.target.value)} placeholder="可以稍後再加入完整內容"/></div><button className="btn-primary h-11">建立作品</button></form>}
    {projects.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{projects.map(project => { const pct = project.shot_count ? Math.round(project.completed_shots/project.shot_count*100) : 0; return <Link to={`/projects/${project.id}`} key={project.id} className="card group p-5 transition hover:-translate-y-0.5 hover:border-blue-200"><div className="mb-5 flex items-start justify-between"><div className="grid h-11 w-11 place-items-center rounded-xl bg-blue-50 text-blue-700"><Video size={21}/></div><ArrowRight className="text-slate-300 transition group-hover:translate-x-1 group-hover:text-blue-600" size={19}/></div><h2 className="font-bold text-slate-900">{project.title}</h2><p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-slate-500">{project.source_text || '尚未加入小說原文'}</p><div className="mt-5"><div className="mb-2 flex justify-between text-xs text-slate-500"><span>{project.completed_shots}/{project.shot_count} 分鏡完成</span><span>{pct}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-600" style={{width:`${pct}%`}}/></div></div><p className="mt-4 text-xs text-slate-400">更新：{formatDate(project.updated_at)}</p></Link> })}</div> : <EmptyState title="未有作品" description="建立第一個作品並加入小說及分鏡"/>}</>
}
