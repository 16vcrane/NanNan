const api = require('../../services/api')
const uploadService = require('../../services/upload')
const { getMoodForScore } = require('../../config/moods')

const POLL_INTERVAL_MS = 1500
const MAX_POLL_COUNT = 40
const NO_REFLECTION_COPY = '这篇日记还没有 AI 回响，但此刻的文字已经被好好保存。'

function formatDetailDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 · ${weekdays[date.getDay()]}`
}

function confirmDeletion() {
  return new Promise((resolve) => {
    wx.showModal({
      title: '确定删除这篇日记吗？',
      content: '删除后将无法恢复。',
      confirmText: '删除',
      confirmColor: '#A94F45',
      success: (result) => resolve(Boolean(result.confirm)),
      fail: () => resolve(false)
    })
  })
}

Page({
  data: {
    diaryId: '',
    diary: null,
    images: [],
    markers: [],
    reflectionStatus: 'pending',
    reflectionContent: '',
    reflectionCanRetry: false,
    reflectionRetrying: false,
    loading: true,
    loadError: false,
    deleting: false
  },

  onLoad(options) {
    this.pollTimer = null
    this.pollCount = 0
    this.isActive = true
    const diaryId = options.diaryId || ''
    this.setData({ diaryId })
    if (!diaryId) {
      this.setData({ loading: false, loadError: true })
      return
    }
    this.loadDetail()
  },

  onShow() {
    this.isActive = true
    if (this.data.diary && this.data.reflectionStatus === 'pending' && !this.pollTimer) {
      this.pollReflection()
    }
  },

  onHide() {
    this.isActive = false
    this.stopPolling()
  },

  onUnload() {
    this.isActive = false
    this.stopPolling()
  },

  async loadDetail() {
    this.stopPolling()
    this.setData({ loading: true, loadError: false })
    try {
      const response = await api.getDiaryDetail(this.data.diaryId)
      const data = response.data
      const mood = getMoodForScore(data.diary.energyScore)
      const reflection = data.reflection || {
        status: 'failed',
        content: NO_REFLECTION_COPY,
        canRetry: false
      }
      const diary = {
        ...data.diary,
        dateText: formatDetailDate(data.diary.createdAt),
        moodText: data.diary.moodLabel || mood.label,
        moodColor: mood.color
      }
      const images = (data.images || []).map((image) => ({
        ...image,
        localPath: '',
        downloadFailed: false
      }))
      this.setData({
        diary,
        images,
        markers: data.markers || [],
        reflectionStatus: reflection.status,
        reflectionContent: reflection.content || '',
        reflectionCanRetry: Boolean(reflection.canRetry),
        loading: false,
        loadError: false
      })
      this.hydrateImages(images)
      if (reflection.status === 'pending') this.schedulePoll()
    } catch (error) {
      this.setData({ loading: false, loadError: true })
    }
  },

  async hydrateImages(images) {
    await Promise.all(images.map(async (image) => {
      try {
        const localPath = await uploadService.downloadImage(image)
        this.updateImage(image.id, { localPath, downloadFailed: false })
      } catch (error) {
        this.updateImage(image.id, { downloadFailed: true })
      }
    }))
  },

  updateImage(imageId, patch) {
    const images = this.data.images.map((image) => (
      image.id === imageId ? { ...image, ...patch } : image
    ))
    this.setData({ images })
  },

  previewImage(event) {
    const imageId = event.currentTarget.dataset.id
    const selected = this.data.images.find((image) => image.id === imageId)
    const urls = this.data.images.map((image) => image.localPath).filter(Boolean)
    if (!selected || !selected.localPath || !urls.length) {
      wx.showToast({ title: '图片还在加载', icon: 'none' })
      return
    }
    wx.previewImage({ current: selected.localPath, urls })
  },

  stopPolling() {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer)
      this.pollTimer = null
    }
  },

  schedulePoll() {
    this.stopPolling()
    if (!this.isActive || this.pollCount >= MAX_POLL_COUNT) return
    this.pollTimer = setTimeout(() => this.pollReflection(), POLL_INTERVAL_MS)
  },

  async pollReflection() {
    this.stopPolling()
    try {
      const response = await api.getReflection(this.data.diaryId)
      const reflection = response.data
      this.pollCount += 1
      this.setData({
        reflectionStatus: reflection.status,
        reflectionContent: reflection.content || '',
        reflectionCanRetry: Boolean(reflection.canRetry)
      })
      if (reflection.status === 'pending') this.schedulePoll()
    } catch (error) {
      this.pollCount += 1
      this.schedulePoll()
    }
  },

  async handleReflectionRetry() {
    if (this.data.reflectionRetrying || !this.data.reflectionCanRetry) return
    this.stopPolling()
    this.setData({ reflectionRetrying: true })
    try {
      await api.retryReflection(this.data.diaryId)
      this.pollCount = 0
      this.setData({
        reflectionStatus: 'pending',
        reflectionContent: '',
        reflectionCanRetry: false,
        reflectionRetrying: false
      })
      this.schedulePoll()
    } catch (error) {
      this.setData({ reflectionRetrying: false })
      wx.showToast({ title: error.message || '暂时无法重试', icon: 'none' })
    }
  },

  async handleDelete() {
    if (this.data.deleting || !(await confirmDeletion())) return
    this.stopPolling()
    this.setData({ deleting: true })
    try {
      await api.deleteDiary(this.data.diaryId)
      wx.showToast({ title: '日记已删除', icon: 'success' })
      wx.navigateBack({
        delta: 1,
        fail: () => wx.switchTab({ url: '/pages/timeline/timeline' })
      })
    } catch (error) {
      this.setData({ deleting: false })
      wx.showToast({ title: error.message || '删除失败，请稍后重试', icon: 'none' })
      if (this.data.reflectionStatus === 'pending') this.schedulePoll()
    }
  }
})

module.exports = { formatDetailDate, confirmDeletion }
