import { statusMeta } from '../lib/status'

const styles = {
  neutral: 'bg-slate-100 text-slate-600', info: 'bg-blue-50 text-blue-700', warning: 'bg-amber-50 text-amber-700',
  success: 'bg-emerald-50 text-emerald-700', danger: 'bg-red-50 text-red-700',
}
export function StatusBadge({ status }: { status: string }) {
  const meta = statusMeta(status)
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${styles[meta.tone]}`}>{meta.label}</span>
}
