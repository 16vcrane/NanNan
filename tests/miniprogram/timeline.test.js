const assert = require('node:assert/strict')
const test = require('node:test')

global.wx = {
  stopPullDownRefresh() {},
  switchTab() {},
  navigateTo(options) {
    global.lastNavigationUrl = options.url
  }
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
    await page.loadDiaries({ reset: true })
  } finally {
    api.getDiaryList = originalGetDiaryList
  }

  assert.equal(page.data.loading, false)
  assert.equal(page.data.loadError, false)
  assert.equal(page.data.diaries[0].markers[0].displayText, '完成')
})

test('timeline appends pages without duplicating diary cards', async () => {
  const originalGetDiaryList = api.getDiaryList
  const requestedPages = []
  api.getDiaryList = async ({ page }) => {
    requestedPages.push(page)
    return {
      data: {
        list: page === 1
          ? [{ id: 'one', content: '第一页', createdAt: '2026-08-15T08:00:00Z' }]
          : [
              { id: 'one', content: '重复项', createdAt: '2026-08-15T08:00:00Z' },
              { id: 'two', content: '第二页', createdAt: '2026-08-14T08:00:00Z' }
            ],
        page,
        hasMore: page === 1
      }
    }
  }
  const page = createPage()

  try {
    await page.loadDiaries({ reset: true })
    await page.loadDiaries()
  } finally {
    api.getDiaryList = originalGetDiaryList
  }

  assert.deepEqual(requestedPages, [1, 2])
  assert.deepEqual(page.data.diaries.map((diary) => diary.id), ['one', 'two'])
  assert.equal(page.data.hasMore, false)
})

test('timeline diary selection opens its detail page', () => {
  global.lastNavigationUrl = ''
  const page = createPage()

  page.handleDiarySelect({ detail: { diaryId: 'diary-3' } })

  assert.equal(global.lastNavigationUrl, '/pages/detail/detail?diaryId=diary-3')
})
