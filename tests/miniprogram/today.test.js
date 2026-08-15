const assert = require('node:assert/strict')
const test = require('node:test')

const storage = new Map()

global.wx = {
  getStorageSync(key) {
    return storage.get(key)
  },
  setStorageSync(key, value) {
    storage.set(key, value)
  },
  removeStorageSync(key) {
    storage.delete(key)
  },
  enableAlertBeforeUnload() {},
  disableAlertBeforeUnload() {},
  showToast() {},
  showModal() {},
  compressImage(options) {
    options.success({ tempFilePath: options.src })
  },
  saveFile(options) {
    options.success({ savedFilePath: options.tempFilePath })
  },
  removeSavedFile() {}
}

global.getApp = () => ({
  globalData: {
    userInfo: { id: 'user-1' }
  },
  loginPromise: Promise.resolve()
})

let pageDefinition
global.Page = (definition) => {
  pageDefinition = definition
}

const { getMoodForScore } = require('../../miniprogram/config/moods')
const draftService = require('../../miniprogram/services/draft')
const api = require('../../miniprogram/services/api')
const auth = require('../../miniprogram/services/auth')
require('../../miniprogram/pages/today/today')

function createPage() {
  return {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    setData(patch) {
      Object.assign(this.data, patch)
    }
  }
}

test('mood mapping covers boundary values', () => {
  assert.equal(getMoodForScore(0).label, '低落')
  assert.equal(getMoodForScore(20).label, '低落')
  assert.equal(getMoodForScore(21).label, '平静')
  assert.equal(getMoodForScore(50).label, '明亮')
  assert.equal(getMoodForScore(100).label, '高亢')
})

test('drafts are isolated by user id', () => {
  draftService.saveDraft('user-a', { content: 'A', energyScore: 20 })
  draftService.saveDraft('user-b', { content: 'B', energyScore: 80 })

  assert.equal(draftService.getDraft('user-a').content, 'A')
  assert.equal(draftService.getDraft('user-b').content, 'B')

  draftService.clearDraft('user-a')
  assert.equal(draftService.getDraft('user-a'), null)
  assert.equal(draftService.getDraft('user-b').content, 'B')
})

test('content input updates count and save state without trimming content', () => {
  const page = createPage()
  page.draftUserId = null
  page.draftTimer = null
  page.isDirty = false

  page.handleContentInput({ detail: { value: '  今天很好。\n' } })

  assert.equal(page.data.content, '  今天很好。\n')
  assert.equal(page.data.charCount, 8)
  assert.equal(page.data.canSave, true)
  assert.equal(page.isDirty, true)
})

test('blank content cannot be saved', () => {
  const page = createPage()
  page.draftUserId = null
  page.draftTimer = null
  page.isDirty = false

  page.handleContentInput({ detail: { value: '   ' } })

  assert.equal(page.data.canSave, false)
})

test('late draft initialization never overwrites current input', async () => {
  draftService.saveDraft('user-1', {
    content: '旧草稿',
    energyScore: 20,
    moodLabel: '低落'
  })
  const page = createPage()
  page.draftTimer = null
  page.draftUserId = null
  page.isDirty = false

  page.handleContentInput({ detail: { value: '刚刚输入的内容' } })
  await page.initializeDraft()

  assert.equal(page.data.content, '刚刚输入的内容')
  assert.equal(draftService.getDraft('user-1').content, '刚刚输入的内容')
})

test('successful save sends the exact draft and resets the editor', async () => {
  const originalCreateDiary = api.createDiary
  const originalEnsureLogin = auth.ensureLogin
  let submittedPayload
  api.createDiary = async (payload) => {
    submittedPayload = payload
    return { data: { diaryId: 'diary-1' } }
  }
  auth.ensureLogin = async () => ({ id: 'user-1' })

  const page = createPage()
  page.draftTimer = null
  page.draftUserId = 'user-1'
  page.isDirty = true
  page.setData({
    content: '原样保存\n第二行',
    charCount: 8,
    energyScore: 73,
    moodLabel: '愉悦',
    canSave: true
  })
  draftService.saveDraft('user-1', submittedPayload || { content: '原样保存\n第二行' })

  try {
    await page.handleSave()
  } finally {
    api.createDiary = originalCreateDiary
    auth.ensureLogin = originalEnsureLogin
  }

  assert.deepEqual(submittedPayload, {
    content: '原样保存\n第二行',
    energyScore: 73,
    moodLabel: '愉悦',
    imageIds: []
  })
  assert.equal(page.data.content, '')
  assert.equal(page.data.saveState, 'success')
  assert.equal(page.isDirty, false)
  assert.equal(draftService.getDraft('user-1'), null)
})

test('save submits only successful images and does not block on failed images', async () => {
  const originalCreateDiary = api.createDiary
  const originalEnsureLogin = auth.ensureLogin
  let submittedPayload
  api.createDiary = async (payload) => {
    submittedPayload = payload
    return { data: { diaryId: 'diary-with-image' } }
  }
  auth.ensureLogin = async () => ({ id: 'user-1' })

  const page = createPage()
  page.draftTimer = null
  page.draftUserId = 'user-1'
  page.isDirty = true
  page.setData({
    content: '文字仍然可以保存',
    images: [
      { localId: 'ok', imageId: 'image-1', status: 'success', localPath: '/ok.jpg' },
      { localId: 'failed', imageId: null, status: 'failed', localPath: '/failed.jpg' }
    ],
    uploadingCount: 0,
    canSave: true
  })

  try {
    await page.handleSave()
  } finally {
    api.createDiary = originalCreateDiary
    auth.ensureLogin = originalEnsureLogin
  }

  assert.deepEqual(submittedPayload.imageIds, ['image-1'])
  assert.equal(page.data.saveState, 'success')
  assert.deepEqual(page.data.images, [])
})

test('drag reorder changes image submission order', () => {
  const page = createPage()
  page.draftUserId = null
  page.draftTimer = null
  page.setData({
    images: [
      { localId: 'first', imageId: 'image-1' },
      { localId: 'second', imageId: 'image-2' },
      { localId: 'third', imageId: 'image-3' }
    ]
  })

  page.handleImageReorder({ detail: { fromIndex: 0, toIndex: 2 } })

  assert.deepEqual(page.data.images.map((image) => image.localId), ['second', 'third', 'first'])
})

test('weak network keeps the draft and reuses the idempotency key', async () => {
  const originalCreateDiary = api.createDiary
  const keys = []
  let attempt = 0
  api.createDiary = async (_payload, key) => {
    keys.push(key)
    attempt += 1
    if (attempt === 1) throw new Error('network unavailable')
    return { data: { diaryId: 'recovered-diary' } }
  }

  const page = createPage()
  page.draftTimer = null
  page.draftUserId = 'user-1'
  page.isDirty = true
  page.setData({ content: '弱网下也不能丢失', canSave: true })

  try {
    await page.handleSave()
    assert.equal(page.data.saveState, 'failed')
    assert.equal(draftService.getDraft('user-1').content, '弱网下也不能丢失')

    await page.handleSave()
  } finally {
    api.createDiary = originalCreateDiary
  }

  assert.equal(keys[0], keys[1])
  assert.equal(page.data.saveState, 'success')
  assert.equal(draftService.getDraft('user-1'), null)
})
