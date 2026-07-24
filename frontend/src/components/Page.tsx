import { LoaderCircle } from 'lucide-react'

export function LoadingScreen() { return <div className="grid min-h-[50vh] place-items-center"><LoaderCircle className="animate-spin text-blue-600" size={28}/></div> }
export function PageHeader({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h1 className="text-2xl font-bold tracking-tight text-slate-950">{title}</h1><p className="mt-1 text-sm text-slate-500">{description}</p></div>{action}</div>
}
export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="card grid min-h-56 place-items-center p-8 text-center"><div><p className="font-semibold text-slate-800">{title}</p><p className="mt-1 text-sm text-slate-500">{description}</p></div></div>
}
