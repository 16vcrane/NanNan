const auth = require('../../services/auth')
const draftService = require('../../services/draft')

function presentUser(user) {
  if (!user) return null
  return {
    ...user,
    shortId: String(user.id || '').slice(0, 8).toUpperCase()
  }
}

function confirmLogout() {
  return new Promise((resolve) => {
    wx.showModal({
      title: '退出当前登录？',
      content: '本机登录态和未保存草稿会被清除，服务端日记不会删除。',
      confirmText: '退出登录',
      success: (result) => resolve(Boolean(result.confirm)),
      fail: () => resolve(false)
    })
  })
}

Page({
  data: {
    user: null,
    loggedIn: false,
    loggingIn: false
  },

  async onShow() {
    const tabBar = this.getTabBar && this.getTabBar()
    if (tabBar) tabBar.setData({ selected: 2 })
    const app = getApp()
    if (app.loginPromise) await app.loginPromise
    this.setData({
      user: presentUser(app.globalData.userInfo),
      loggedIn: Boolean(app.globalData.userInfo)
    })
  },

  openAiInfo() {
    wx.navigateTo({
      url: '/pages/ai-info/ai-info'
    })
  },

  openPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' })
  },

  openAgreement() {
    wx.navigateTo({ url: '/pages/user-agreement/user-agreement' })
  },

  openDataManagement() {
    wx.navigateTo({ url: '/pages/data-management/data-management' })
  },

  async handleLogin() {
    if (this.data.loggingIn) return
    this.setData({ loggingIn: true })
    try {
      const user = await auth.ensureLogin({ force: true })
      this.setData({
        user: presentUser(user),
        loggedIn: Boolean(user),
        loggingIn: false
      })
    } catch (error) {
      this.setData({ loggingIn: false })
      wx.showToast({ title: '登录失败，请稍后重试', icon: 'none' })
    }
  },

  async handleLogout() {
    if (!this.data.user || !(await confirmLogout())) return
    draftService.discardDraft(this.data.user.id)
    auth.clearLogin({ intentional: true })
    this.setData({ user: null, loggedIn: false })
    wx.showToast({ title: '已退出登录', icon: 'success' })
    wx.reLaunch({ url: '/pages/today/today' })
  }
})

module.exports = { presentUser, confirmLogout }
