const assert = require('node:assert/strict')
const test = require('node:test')

let navigatedBack = false
global.wx = {
  showModal(options) {
    options.success({ confirm: true, cancel: false })
  },
  showToast() {},
  navigateBack() {
    navigatedBack = true
  },
  switchTab() {},
  previewImage() {}
}

let pageDefinition
global.Page = (definition) => {
  pageDefinition = definition
}

const api = require('../../miniprogram/services/api')
const { formatDetailDate } = require('../../miniprogram/pages/detail/detail')

function createPage() {
  return {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    pollTimer: null,
    pollCount: 0,
    isActive: true,
    setData(patch) {
      Object.assign(this.data, patch)
    }
  }
}

test('detail page preserves full diary content and related data', async () => {
  const originalGetDiaryDetail = api.getDiaryDetail
  api.getDiaryDetail = async () => ({
    data: {
      diary: {
        id: 'diary-1',
        content: '第一行\n第二行保持原样',
        energyScore: 70,
        moodLabel: '愉悦',
        createdAt: '2026-08-15T08:00:00Z'
      },
      images: [],
      markers: [{ id: 'marker-1', displayText: '完成', color: '#789184' }],
      reflection: {
        status: 'success',
        content: '你把今天完成的事情认真写了下来，也为这一刻留住了一份清晰而温柔的记忆。',
        canRetry: false
      }
    }
  })
  const page = createPage()
  page.setData({ diaryId: 'diary-1' })

  try {
    await page.loadDetail()
  } finally {
    api.getDiaryDetail = originalGetDiaryDetail
  }

  assert.equal(page.data.diary.content, '第一行\n第二行保持原样')
  assert.equal(page.data.markers[0].displayText, '完成')
  assert.equal(page.data.reflectionStatus, 'success')
  assert.equal(page.data.loading, false)
  assert.match(formatDetailDate('2026-08-15T08:00:00Z'), /2026年/)
})

test('confirmed deletion calls the API and returns to timeline', async () => {
  const originalDeleteDiary = api.deleteDiary
  let deletedDiaryId
  navigatedBack = false
  api.deleteDiary = async (diaryId) => {
    deletedDiaryId = diaryId
    return { data: { deleted: true } }
  }
  const page = createPage()
  page.setData({ diaryId: 'diary-2', reflectionStatus: 'success' })

  try {
    await page.handleDelete()
  } finally {
    api.deleteDiary = originalDeleteDiary
  }

  assert.equal(deletedDiaryId, 'diary-2')
  assert.equal(navigatedBack, true)
})
