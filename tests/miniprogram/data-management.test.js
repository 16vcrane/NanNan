const assert = require('node:assert/strict')
const test = require('node:test')

const localStorage = new Map()
let relaunchedTo = ''

global.wx = {
  getStorageSync(key) {
    return localStorage.get(key)
  },
  setStorageSync(key, value) {
    localStorage.set(key, value)
  },
  removeStorageSync(key) {
    localStorage.delete(key)
  },
  removeSavedFile() {},
  showModal(options) {
    options.success({ confirm: true, cancel: false })
  },
  showToast() {},
  reLaunch(options) {
    relaunchedTo = options.url
  }
}

const app = {
  globalData: {
    userInfo: { id: 'user-8' },
    accessToken: 'token',
    authStatus: 'authenticated'
  }
}
global.getApp = () => app

let pageDefinition
global.Page = (definition) => {
  pageDefinition = definition
}

const api = require('../../miniprogram/services/api')
const storage = require('../../miniprogram/utils/storage')
const draftService = require('../../miniprogram/services/draft')
require('../../miniprogram/pages/data-management/data-management')

function createPage() {
  return {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    setData(patch) {
      Object.assign(this.data, patch)
    }
  }
}

test('account deletion clears server and local user data state', async () => {
  const originalDeleteCurrentUser = api.deleteCurrentUser
  let deleteRequested = false
  api.deleteCurrentUser = async () => {
    deleteRequested = true
    return { data: { deleted: true } }
  }
  storage.setAccessToken('token')
  storage.setAuthUser({ id: 'user-8' })
  draftService.saveDraft('user-8', { content: '未保存内容', images: [] })
  localStorage.set('nannan_image_cleanup_v1_user-8', ['image-1'])
  relaunchedTo = ''
  const page = createPage()
  page.setData({ user: { id: 'user-8' } })

  try {
    await page.handleDeleteAll()
  } finally {
    api.deleteCurrentUser = originalDeleteCurrentUser
  }

  assert.equal(deleteRequested, true)
  assert.equal(storage.getAccessToken(), '')
  assert.equal(storage.isLoggedOut(), true)
  assert.equal(draftService.getDraft('user-8'), null)
  assert.equal(localStorage.has('nannan_image_cleanup_v1_user-8'), false)
  assert.equal(app.globalData.userInfo, null)
  assert.equal(relaunchedTo, '/pages/today/today')
})
