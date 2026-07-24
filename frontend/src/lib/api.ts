export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' })
  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try { message = (await response.json()).detail ?? message } catch { /* non-json */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const formatDate = (iso?: string) => iso ? new Intl.DateTimeFormat('zh-HK', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Hong_Kong'
}).format(new Date(iso)) : '—'
