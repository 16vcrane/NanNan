const assert = require('node:assert/strict')
const test = require('node:test')

global.wx = {
  showToast() {},
  switchTab() {}
}

let pageDefinition
global.Page = (definition) => {
  pageDefinition = definition
}

const api = require('../../miniprogram/services/api')
require('../../miniprogram/pages/reflection/reflection')

function createPage() {
  return {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    pollCount: 0,
    pollTimer: null,
    isActive: true,
    setData(patch) {
      Object.assign(this.data, patch)
    }
  }
}

test('reflection page renders a successful result from the polling API', async () => {
  const originalGetReflection = api.getReflection
  api.getReflection = async () => ({
    data: {
      status: 'success',
      content: '你把今天完成项目的认真留在了这一页，也为这段忙碌保留了一份清晰而温柔的注脚。',
      canRetry: false
    }
  })
  const page = createPage()
  page.setData({ diaryId: 'diary-1' })

  try {
    await page.fetchReflection()
  } finally {
    api.getReflection = originalGetReflection
  }

  assert.equal(page.data.status, 'success')
  assert.match(page.data.content, /完成项目/)
  assert.equal(page.data.canRetry, false)
  assert.equal(page.pollTimer, null)
})

test('failed reflection can be reset to pending for a limited retry', async () => {
  const originalRetryReflection = api.retryReflection
  let requestedDiaryId
  api.retryReflection = async (diaryId) => {
    requestedDiaryId = diaryId
    return { data: { status: 'pending', attemptCount: 1 } }
  }
  const page = createPage()
  page.setData({
    diaryId: 'diary-2',
    status: 'failed',
    content: 'fallback',
    canRetry: true
  })
  page.schedulePoll = function schedulePoll() {
    this.pollScheduled = true
  }

  try {
    await page.handleRetry()
  } finally {
    api.retryReflection = originalRetryReflection
  }

  assert.equal(requestedDiaryId, 'diary-2')
  assert.equal(page.data.status, 'pending')
  assert.equal(page.data.content, '')
  assert.equal(page.data.canRetry, false)
  assert.equal(page.pollScheduled, true)
})
