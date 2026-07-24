import { Upload } from 'lucide-react'
import { useId, useState } from 'react'
import { api } from '../lib/api'

type UploadedMedia = { url: string; name: string; size: number }

type Props = {
  label: string
  accept: string
  value?: string
  onChange: (url: string) => void
}

export function AssetUploadField({ label, accept, value, onChange }: Props) {
  const id = useId()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function upload(file?: File) {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const body = new FormData()
      body.append('file', file)
      const result = await api<UploadedMedia>('/api/media/upload', { method: 'POST', body })
      onChange(result.url)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '上載失敗')
    } finally {
      setBusy(false)
    }
  }

  return <div>
    <label className="label" htmlFor={id}>{label}</label>
    <label className="field flex cursor-pointer items-center gap-2" htmlFor={id}>
      <Upload size={15}/>
      <span className="min-w-0 flex-1 truncate text-sm">{busy ? '上載中…' : value?.split('/').pop() || '選擇檔案'}</span>
    </label>
    <input
      id={id}
      className="sr-only"
      type="file"
      accept={accept}
      disabled={busy}
      onChange={event => void upload(event.target.files?.[0])}
    />
    {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
  </div>
}
