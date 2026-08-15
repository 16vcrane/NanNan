const api = require('../../services/api')
const uploadService = require('../../services/upload')
const { getMoodForScore } = require('../../config/moods')

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
  const mood = getMoodForScore(diary.energyScore)
  return {
    ...diary,
    dateText: formatDate(diary.createdAt),
    summary: summarize(diary.content || ''),
    moodText: diary.moodLabel || mood.label,
    moodColor: mood.color,
    markers: diary.markers || [],
    images: diary.images || [],
    thumbnailPath: ''
  }
}

function mergeDiaries(current, incoming) {
  const ids = new Set(current.map((diary) => diary.id))
  return [...current, ...incoming.filter((diary) => !ids.has(diary.id))]
}

Page({
  data: {
    diaries: [],
    loading: true,
    refreshing: false,
    loadingMore: false,
    loadError: false,
    loadMoreError: false,
    page: 0,
    hasMore: true
  },

  onLoad() {
    this.requestId = 0
    this.thumbnailCache = {}
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar()
    if (tabBar) tabBar.setData({ selected: 1 })
    this.loadDiaries({ reset: true })
  },

  async loadDiaries(options = {}) {
    const reset = Boolean(options.reset)
    if (reset && this.data.refreshing) return
    if (!reset && (this.data.loading || this.data.loadingMore || !this.data.hasMore)) return

    const targetPage = reset ? 1 : this.data.page + 1
    this.requestId = (this.requestId || 0) + 1
    const requestId = this.requestId
    if (!this.thumbnailCache) this.thumbnailCache = {}
    this.setData({
      loading: reset && !this.data.diaries.length,
      refreshing: reset && Boolean(this.data.diaries.length),
      loadingMore: !reset,
      loadError: false,
      loadMoreError: false
    })
    try {
      const response = await api.getDiaryList({ page: targetPage, limit: 20 })
      if (requestId !== this.requestId) return
      const presented = (response.data.list || []).map(presentDiary)
      const diaries = reset
        ? presented
        : mergeDiaries(this.data.diaries, presented)
      this.setData({
        diaries,
        page: response.data.page,
        hasMore: Boolean(response.data.hasMore),
        loading: false,
        refreshing: false,
        loadingMore: false,
        loadError: false
      })
      this.hydrateThumbnails(presented)
    } catch (error) {
      if (requestId !== this.requestId) return
      this.setData({
        loading: false,
        refreshing: false,
        loadingMore: false,
        loadError: reset && !this.data.diaries.length,
        loadMoreError: !reset || Boolean(this.data.diaries.length)
      })
    } finally {
      if (wx.stopPullDownRefresh) wx.stopPullDownRefresh()
    }
  },

  async hydrateThumbnails(diaries) {
    await Promise.all(diaries.map(async (diary) => {
      const image = diary.images[0]
      if (!image) return
      if (this.thumbnailCache[image.id]) {
        this.setThumbnail(diary.id, this.thumbnailCache[image.id])
        return
      }
      try {
        const localPath = await uploadService.downloadImage(image)
        this.thumbnailCache[image.id] = localPath
        this.setThumbnail(diary.id, localPath)
      } catch (error) {
        // The diary remains readable when its thumbnail cannot be downloaded.
      }
    }))
  },

  setThumbnail(diaryId, thumbnailPath) {
    const diaries = this.data.diaries.map((diary) => (
      diary.id === diaryId ? { ...diary, thumbnailPath } : diary
    ))
    this.setData({ diaries })
  },

  onPullDownRefresh() {
    this.loadDiaries({ reset: true })
  },

  onReachBottom() {
    this.loadDiaries()
  },

  handleDiarySelect(event) {
    const diaryId = event.detail.diaryId
    if (!diaryId) return
    wx.navigateTo({ url: `/pages/detail/detail?diaryId=${diaryId}` })
  },

  goToToday() {
    wx.switchTab({ url: '/pages/today/today' })
  }
})

module.exports = { formatDate, summarize, presentDiary, mergeDiaries }
