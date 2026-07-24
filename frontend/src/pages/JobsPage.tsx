import { RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { EmptyState, LoadingScreen, PageHeader } from '../components/Page'
import { StatusBadge } from '../components/StatusBadge'
import { api, formatDate } from '../lib/api'
import type { Job } from '../types'

export function JobsPage() {
  const [jobs,setJobs]=useState<Job[]|null>(null); const load=()=>api<Job[]>('/api/jobs').then(setJobs)
  useEffect(()=>{void load();const timer=setInterval(load,2500);return()=>clearInterval(timer)},[])
  if(!jobs)return <LoadingScreen/>
  return <><PageHeader title="生成隊列" description="追蹤每個短鏡嘅排隊、生成、上載及錯誤狀態" action={<button className="btn-secondary" onClick={()=>void load()}><RefreshCw size={16}/>更新</button>}/>{jobs.length?<div className="card overflow-hidden"><div className="hidden grid-cols-[1.3fr_1fr_110px_100px_150px] gap-4 border-b bg-slate-50 px-5 py-3 text-xs font-semibold uppercase text-slate-500 md:grid"><span>任務</span><span>引擎</span><span>進度</span><span>狀態</span><span>建立時間</span></div><div className="divide-y">{jobs.map(job=><div key={job.id} className="grid gap-3 px-5 py-4 md:grid-cols-[1.3fr_1fr_110px_100px_150px] md:items-center"><div><p className="text-sm font-semibold">{job.shot_title}</p><p className="mt-1 text-xs text-slate-500">{job.project_title}</p></div><code className="text-xs text-slate-600">{job.engine}</code><div><div className="h-1.5 rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-600" style={{width:`${job.progress}%`}}/></div><p className="mt-1 text-[11px] text-slate-400">{job.progress}%</p></div><StatusBadge status={job.status}/><span className="text-xs text-slate-500">{formatDate(job.created_at)}</span>{job.error&&<p className="col-span-full rounded bg-red-50 p-2 text-xs text-red-700">{job.error}</p>}</div>)}</div></div>:<EmptyState title="隊列為空" description="由作品分鏡頁將鏡頭加入生成隊列"/>}</>
}
