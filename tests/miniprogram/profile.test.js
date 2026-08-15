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
    userInfo: { id: '12345678-abcd' },
    accessToken: 'token',
    authStatus: 'authenticated'
  }
}
global.getApp = () => app

let pageDefinition
global.Page = (definition) => {
  pageDefinition = definition
}

const storage = require('../../miniprogram/utils/storage')
const draftService = require('../../miniprogram/services/draft')
const { presentUser } = require('../../miniprogram/pages/profile/profile')

function createPage() {
  return {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    setData(patch) {
      Object.assign(this.data, patch)
    }
  }
}

test('profile exposes only a shortened application user id', () => {
  assert.equal(presentUser({ id: '12345678-abcd' }).shortId, '12345678')
})

test('intentional logout clears local auth and unsaved draft', async () => {
  storage.setAccessToken('token')
  storage.setAuthUser({ id: '12345678-abcd' })
  draftService.saveDraft('12345678-abcd', { content: '草稿', images: [] })
  relaunchedTo = ''
  const page = createPage()
  page.setData({ user: { id: '12345678-abcd' }, loggedIn: true })

  await page.handleLogout()

  assert.equal(storage.getAccessToken(), '')
  assert.equal(storage.isLoggedOut(), true)
  assert.equal(draftService.getDraft('12345678-abcd'), null)
  assert.equal(app.globalData.userInfo, null)
  assert.equal(relaunchedTo, '/pages/today/today')
})
