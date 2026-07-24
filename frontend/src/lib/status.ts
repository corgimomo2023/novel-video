export type StatusTone = 'neutral' | 'info' | 'warning' | 'success' | 'danger'

const values: Record<string, { label: string; tone: StatusTone }> = {
  draft: { label: '草稿', tone: 'neutral' },
  queued: { label: '排隊中', tone: 'warning' },
  running: { label: '生成中', tone: 'info' },
  completed: { label: '已完成', tone: 'success' },
  failed: { label: '失敗', tone: 'danger' },
}

export function statusMeta(status: string) {
  return values[status] ?? { label: '未知', tone: 'neutral' as StatusTone }
}
