const api = require('../../services/api')

const POLL_INTERVAL_MS = 1500
const MAX_POLL_COUNT = 40

Page({
  data: {
    diaryId: '',
    status: 'pending',
    content: '',
    canRetry: false,
    retrying: false,
    loadError: false
  },

  onLoad(options) {
    this.pollCount = 0
    this.pollTimer = null
    this.isActive = true
    this.setData({ diaryId: options.diaryId || '' })
    if (!options.diaryId) {
      this.setData({ status: 'failed', loadError: true })
      return
    }
    this.fetchReflection()
  },

  onUnload() {
    this.isActive = false
    this.stopPolling()
  },

  onHide() {
    this.isActive = false
    this.stopPolling()
  },

  onShow() {
    this.isActive = true
    if (this.data.diaryId && this.pollCount > 0 && this.data.status === 'pending') {
      this.fetchReflection()
    }
  },

  stopPolling() {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer)
      this.pollTimer = null
    }
  },

  schedulePoll() {
    this.stopPolling()
    if (!this.isActive) return
    if (this.pollCount >= MAX_POLL_COUNT) {
      this.setData({ loadError: true })
      return
    }
    this.pollTimer = setTimeout(() => this.fetchReflection(), POLL_INTERVAL_MS)
  },

  async fetchReflection() {
    try {
      const response = await api.getReflection(this.data.diaryId)
      const reflection = response.data
      this.pollCount += 1
      this.setData({
        status: reflection.status,
        content: reflection.content || '',
        canRetry: Boolean(reflection.canRetry),
        loadError: false
      })
      if (reflection.status === 'pending') this.schedulePoll()
    } catch (error) {
      this.pollCount += 1
      this.setData({ loadError: true })
      this.schedulePoll()
    }
  },

  async handleRetry() {
    if (this.data.retrying || !this.data.canRetry) return
    this.stopPolling()
    this.setData({ retrying: true })
    try {
      await api.retryReflection(this.data.diaryId)
      this.pollCount = 0
      this.setData({
        status: 'pending',
        content: '',
        canRetry: false,
        retrying: false,
        loadError: false
      })
      this.schedulePoll()
    } catch (error) {
      this.setData({ retrying: false })
      wx.showToast({ title: error.message || '暂时无法重试', icon: 'none' })
    }
  },

  goToTimeline() {
    wx.switchTab({ url: '/pages/timeline/timeline' })
  },

  goToToday() {
    wx.switchTab({ url: '/pages/today/today' })
  }
})
