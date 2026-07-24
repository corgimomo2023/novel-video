import { describe, expect, it } from 'vitest'
import { statusMeta } from './status'

describe('statusMeta', () => {
  it('maps every persisted shot lifecycle to readable Traditional Chinese', () => {
    expect(statusMeta('draft').label).toBe('草稿')
    expect(statusMeta('queued').label).toBe('排隊中')
    expect(statusMeta('running').label).toBe('生成中')
    expect(statusMeta('completed').label).toBe('已完成')
    expect(statusMeta('failed').label).toBe('失敗')
  })

  it('does not present unknown server states as completed', () => {
    expect(statusMeta('unexpected').label).toBe('未知')
    expect(statusMeta('unexpected').tone).toBe('neutral')
  })
})
