const assert = require('node:assert/strict')
const test = require('node:test')

global.wx = {
  stopPullDownRefresh() {},
  switchTab() {}
}

let pageDefinition
global.Page = (definition) => {
  pageDefinition = definition
}

const api = require('../../miniprogram/services/api')
const { presentDiary, summarize } = require('../../miniprogram/pages/timeline/timeline')

function createPage() {
  return {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    setData(patch) {
      Object.assign(this.data, patch)
    }
  }
}

test('timeline presentation keeps marker metadata and limits summaries', () => {
  const content = '记'.repeat(81)
  const diary = presentDiary({
    id: 'diary-1',
    content,
    createdAt: '2026-08-15T08:00:00Z',
    moodLabel: '明亮',
    markers: [{ id: 'marker-1', displayText: '完成', color: '#789184' }]
  })

  assert.equal(diary.summary.length, 81)
  assert.equal(diary.summary.endsWith('…'), true)
  assert.equal(diary.markers[0].displayText, '完成')
  assert.equal(summarize('短日记'), '短日记')
})

test('timeline loads the first diary page and exposes its markers', async () => {
  const originalGetDiaryList = api.getDiaryList
  api.getDiaryList = async () => ({
    data: {
      list: [{
        id: 'diary-2',
        content: '今天完成了作品。',
        createdAt: '2026-08-15T08:00:00Z',
        moodLabel: '愉悦',
        markers: [{ id: 'marker-2', displayText: '完成', color: '#789184' }]
      }]
    }
  })
  const page = createPage()

  try {
    await page.loadDiaries()
  } finally {
    api.getDiaryList = originalGetDiaryList
  }

  assert.equal(page.data.loading, false)
  assert.equal(page.data.loadError, false)
  assert.equal(page.data.diaries[0].markers[0].displayText, '完成')
})
