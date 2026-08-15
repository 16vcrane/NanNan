const api = require('../../services/api')

function formatDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}.${month}.${day}`
}

function summarize(content) {
  if (content.length <= 80) return content
  return `${content.slice(0, 80)}…`
}

function presentDiary(diary) {
  return {
    ...diary,
    dateText: formatDate(diary.createdAt),
    summary: summarize(diary.content || ''),
    moodText: diary.moodLabel || '平静',
    markers: diary.markers || []
  }
}

Page({
  data: {
    diaries: [],
    loading: true,
    loadError: false
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar()
    if (tabBar) tabBar.setData({ selected: 1 })
    this.loadDiaries()
  },

  async loadDiaries() {
    if (!this.data.diaries.length) {
      this.setData({ loading: true })
    }
    try {
      const response = await api.getDiaryList({ page: 1, limit: 20 })
      this.setData({
        diaries: (response.data.list || []).map(presentDiary),
        loading: false,
        loadError: false
      })
    } catch (error) {
      this.setData({ loading: false, loadError: true })
    } finally {
      if (wx.stopPullDownRefresh) wx.stopPullDownRefresh()
    }
  },

  onPullDownRefresh() {
    this.loadDiaries()
  },

  goToToday() {
    wx.switchTab({ url: '/pages/today/today' })
  }
})

module.exports = { formatDate, summarize, presentDiary }
