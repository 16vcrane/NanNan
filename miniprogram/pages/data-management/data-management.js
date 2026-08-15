const api = require('../../services/api')
const auth = require('../../services/auth')
const draftService = require('../../services/draft')
const uploadService = require('../../services/upload')

function confirmDeleteAll() {
  return new Promise((resolve) => {
    wx.showModal({
      title: '永久删除全部数据？',
      content: '账户、日记、图片和 AI 回响都将删除，且无法恢复。',
      confirmText: '永久删除',
      confirmColor: '#A94F45',
      success: (result) => resolve(Boolean(result.confirm)),
      fail: () => resolve(false)
    })
  })
}

Page({
  data: {
    user: null,
    deleting: false,
    loggingIn: false
  },

  async onShow() {
    const app = getApp()
    if (app.loginPromise) await app.loginPromise
    this.syncUser()
  },

  syncUser() {
    const user = getApp().globalData.userInfo
    this.setData({ user: user || null })
  },

  async handleLogin() {
    if (this.data.loggingIn) return
    this.setData({ loggingIn: true })
    try {
      const user = await auth.ensureLogin({ force: true })
      this.setData({ user, loggingIn: false })
    } catch (error) {
      this.setData({ loggingIn: false })
      wx.showToast({ title: '登录失败，请稍后重试', icon: 'none' })
    }
  },

  async handleDeleteAll() {
    if (!this.data.user || this.data.deleting || !(await confirmDeleteAll())) return
    const userId = this.data.user.id
    this.setData({ deleting: true })
    try {
      await api.deleteCurrentUser()
      draftService.discardDraft(userId)
      uploadService.clearCleanup(userId)
      auth.clearLogin({ intentional: true })
      wx.showToast({ title: '全部数据已删除', icon: 'success' })
      wx.reLaunch({ url: '/pages/today/today' })
    } catch (error) {
      this.setData({ deleting: false })
      wx.showToast({ title: error.message || '删除失败，请稍后重试', icon: 'none' })
    }
  }
})

module.exports = { confirmDeleteAll }
