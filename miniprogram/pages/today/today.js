const api = require('../../services/api')
const auth = require('../../services/auth')
const draftService = require('../../services/draft')
const uploadService = require('../../services/upload')
const { getMoodForScore } = require('../../config/moods')

const MAX_CONTENT_LENGTH = 3000
const DRAFT_DELAY_MS = 600
const DEFAULT_ENERGY_SCORE = 50

function createIdempotencyKey() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`
}

function getNavigationMetrics() {
  const fallback = {
    statusBarHeight: 20,
    navBarHeight: 44,
    navRightInset: 96
  }
  try {
    const windowInfo = wx.getWindowInfo
      ? wx.getWindowInfo()
      : wx.getSystemInfoSync()
    const menu = wx.getMenuButtonBoundingClientRect
      ? wx.getMenuButtonBoundingClientRect()
      : null
    const statusBarHeight = windowInfo.statusBarHeight || fallback.statusBarHeight
    if (!menu || !menu.height || !menu.top) {
      return { ...fallback, statusBarHeight }
    }
    return {
      statusBarHeight,
      navBarHeight: menu.height + Math.max(0, menu.top - statusBarHeight) * 2,
      navRightInset: Math.max(88, windowInfo.windowWidth - menu.left + 8)
    }
  } catch (error) {
    return fallback
  }
}

function formatToday(date) {
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${date.getMonth() + 1}月${date.getDate()}日 · ${weekdays[date.getDay()]}`
}

function greetingForHour(hour) {
  if (hour < 6) return '夜深了，写下此刻也很好'
  if (hour < 11) return '早上好，给今天留一页'
  if (hour < 14) return '中午好，停下来看看自己'
  if (hour < 18) return '下午好，记下这一刻'
  return '晚上好，今天辛苦了'
}

function compressImage(filePath) {
  return new Promise((resolve, reject) => {
    wx.compressImage({
      src: filePath,
      quality: 80,
      compressedWidth: 1600,
      success: (result) => resolve(result.tempFilePath),
      fail: (error) => reject(new Error(error.errMsg || '图片压缩失败'))
    })
  })
}

function persistLocalImage(filePath) {
  return new Promise((resolve) => {
    wx.saveFile({
      tempFilePath: filePath,
      success: (result) => resolve({
        localPath: result.savedFilePath,
        savedFile: true
      }),
      fail: () => resolve({ localPath: filePath, savedFile: false })
    })
  })
}

function removeLocalImage(image) {
  if (!image.savedFile || !image.localPath || !wx.removeSavedFile) return
  wx.removeSavedFile({ filePath: image.localPath })
}

function localFileExists(filePath) {
  if (!filePath) return Promise.resolve(false)
  if (!wx.getFileSystemManager) return Promise.resolve(true)
  return new Promise((resolve) => {
    wx.getFileSystemManager().access({
      path: filePath,
      success: () => resolve(true),
      fail: () => resolve(false)
    })
  })
}

function canSubmit(content, images, saving) {
  const uploading = images.some((image) => (
    image.status === 'pending' || image.status === 'uploading'
  ))
  return Boolean(content.trim()) && !uploading && !saving
}

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    navRightInset: 96,
    dateText: '',
    greeting: '',
    content: '',
    charCount: 0,
    maxLength: MAX_CONTENT_LENGTH,
    energyScore: DEFAULT_ENERGY_SCORE,
    moodLabel: getMoodForScore(DEFAULT_ENERGY_SCORE).label,
    images: [],
    uploadingCount: 0,
    saving: false,
    canSave: false,
    saveState: 'idle',
    draftStatus: ''
  },

  onLoad() {
    const now = new Date()
    const navigation = getNavigationMetrics()
    this.draftTimer = null
    this.draftUserId = null
    this.saveIdempotencyKey = null
    this.isDirty = false
    this.setData({
      ...navigation,
      dateText: formatToday(now),
      greeting: greetingForHour(now.getHours())
    })
    this.initializeDraft()
  },

  onHide() {
    this.persistDraft()
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar()
    if (tabBar) tabBar.setData({ selected: 0 })
  },

  onUnload() {
    this.clearDraftTimer()
    this.persistDraft()
  },

  async initializeDraft() {
    const app = getApp()
    if (app.loginPromise) {
      await app.loginPromise
    }
    const user = app.globalData.userInfo
    if (!user || !user.id) {
      this.setData({ draftStatus: '登录后可自动保存草稿' })
      return
    }

    this.draftUserId = user.id
    uploadService.flushCleanup(this.draftUserId)
    if (this.isDirty) {
      this.persistDraft()
      return
    }
    const draft = draftService.getDraft(this.draftUserId)
    if (!draft) return

    const content = draft.content || ''
    const energyScore = Number.isFinite(draft.energyScore)
      ? draft.energyScore
      : DEFAULT_ENERGY_SCORE
    const images = (draft.images || []).map((image) => ({
      ...image,
      status: image.status === 'pending' || image.status === 'uploading'
        ? 'failed'
        : image.status
    }))
    this.isDirty = true
    this.setData({
      content,
      charCount: content.length,
      energyScore,
      moodLabel: draft.moodLabel || getMoodForScore(energyScore).label,
      images,
      uploadingCount: 0,
      canSave: canSubmit(content, images, false),
      draftStatus: '已恢复上次草稿'
    })
    this.hydrateRemoteImages(images)
    this.updateUnloadAlert()
  },

  handleContentInput(event) {
    const content = event.detail.value
    this.markDirty()
    this.setData({
      content,
      charCount: content.length,
      canSave: canSubmit(content, this.data.images, this.data.saving),
      saveState: 'idle'
    })
    this.scheduleDraft()
  },

  handleMoodChange(event) {
    this.markDirty()
    this.setData({
      energyScore: event.detail.value,
      moodLabel: event.detail.label,
      saveState: 'idle'
    })
    this.scheduleDraft()
  },

  markDirty() {
    if (!this.data.saving) this.saveIdempotencyKey = null
    this.isDirty = true
    this.updateUnloadAlert()
  },

  updateUnloadAlert() {
    if (this.isDirty && wx.enableAlertBeforeUnload) {
      wx.enableAlertBeforeUnload({
        message: '这篇日记还没有保存，确定要离开吗？'
      })
      return
    }
    if (!this.isDirty && wx.disableAlertBeforeUnload) {
      wx.disableAlertBeforeUnload()
    }
  },

  clearDraftTimer() {
    if (this.draftTimer) {
      clearTimeout(this.draftTimer)
      this.draftTimer = null
    }
  },

  scheduleDraft() {
    this.clearDraftTimer()
    if (!this.draftUserId) return
    this.draftTimer = setTimeout(() => {
      this.persistDraft()
    }, DRAFT_DELAY_MS)
  },

  persistDraft() {
    if (!this.isDirty || !this.draftUserId) return
    this.clearDraftTimer()
    draftService.saveDraft(this.draftUserId, {
      content: this.data.content,
      energyScore: this.data.energyScore,
      moodLabel: this.data.moodLabel,
      images: this.data.images
    })
    this.setData({ draftStatus: '已自动保存草稿' })
  },

  async hydrateRemoteImages(images) {
    for (const image of images) {
      if (image.status !== 'success' || !image.imageId) continue
      try {
        if (await localFileExists(image.localPath)) continue
        const localPath = await uploadService.downloadImage({
          id: image.imageId,
          url: image.url
        })
        this.updateImage(image.localId, { localPath })
      } catch (error) {
        // The server copy remains valid; preview can be retried after the network recovers.
      }
    }
  },

  updateImage(localId, patch) {
    const images = this.data.images.map((image) => (
      image.localId === localId ? { ...image, ...patch } : image
    ))
    const uploadingCount = images.filter((image) => (
      image.status === 'pending' || image.status === 'uploading'
    )).length
    this.setData({
      images,
      uploadingCount,
      canSave: canSubmit(this.data.content, images, this.data.saving)
    })
    this.scheduleDraft()
  },

  handleImageSelect(event) {
    const available = Math.max(0, 3 - this.data.images.length)
    const files = event.detail.files.slice(0, available)
    if (!files.length) return

    const now = Date.now()
    const added = files.map((file, index) => ({
      localId: `${now}-${index}-${Math.random().toString(16).slice(2)}`,
      localPath: file.tempFilePath,
      savedFile: false,
      imageId: null,
      url: '',
      status: 'pending',
      error: ''
    }))
    const images = [...this.data.images, ...added]
    this.markDirty()
    this.setData({
      images,
      uploadingCount: images.filter((image) => (
        image.status === 'pending' || image.status === 'uploading'
      )).length,
      canSave: false
    })
    this.scheduleDraft()
    added.forEach((image) => this.prepareAndUploadImage(image))
  },

  async prepareAndUploadImage(image) {
    try {
      const compressedPath = await compressImage(image.localPath)
      const persisted = await persistLocalImage(compressedPath)
      this.updateImage(image.localId, {
        ...persisted,
        status: 'uploading',
        error: ''
      })
      await this.uploadPreparedImage(image.localId, persisted.localPath)
    } catch (error) {
      this.updateImage(image.localId, {
        status: 'failed',
        error: error.message || '图片处理失败'
      })
    }
  },

  async uploadPreparedImage(localId, localPath) {
    try {
      const uploaded = await uploadService.uploadImage(localPath)
      this.updateImage(localId, {
        imageId: uploaded.id,
        url: uploaded.url,
        status: 'success',
        error: ''
      })
    } catch (error) {
      this.updateImage(localId, {
        status: 'failed',
        error: error.message || '图片上传失败'
      })
    }
  },

  handleImageRetry(event) {
    const image = this.data.images.find((item) => item.localId === event.detail.localId)
    if (!image || !image.localPath) return
    this.updateImage(image.localId, { status: 'uploading', error: '' })
    this.uploadPreparedImage(image.localId, image.localPath)
  },

  handleImageReorder(event) {
    const fromIndex = Number(event.detail.fromIndex)
    const toIndex = Number(event.detail.toIndex)
    if (
      fromIndex === toIndex ||
      fromIndex < 0 ||
      toIndex < 0 ||
      fromIndex >= this.data.images.length ||
      toIndex >= this.data.images.length
    ) return

    const images = [...this.data.images]
    const [moved] = images.splice(fromIndex, 1)
    images.splice(toIndex, 0, moved)
    this.markDirty()
    this.setData({ images })
    this.scheduleDraft()
  },

  handleImageRemove(event) {
    const image = this.data.images.find((item) => item.localId === event.detail.localId)
    if (!image) return
    if (image.status === 'pending' || image.status === 'uploading') {
      wx.showToast({ title: '图片正在处理', icon: 'none' })
      return
    }

    const images = this.data.images.filter((item) => item.localId !== image.localId)
    this.markDirty()
    this.setData({
      images,
      uploadingCount: 0,
      canSave: canSubmit(this.data.content, images, this.data.saving)
    })
    removeLocalImage(image)
    if (image.imageId) {
      uploadService.deleteImage(image.imageId).catch(() => {
        uploadService.enqueueCleanup(this.draftUserId, image.imageId)
      })
    }
    this.scheduleDraft()
  },

  async handleSave() {
    if (this.data.saving) return
    if (this.data.uploadingCount > 0) {
      wx.showToast({ title: '请等待图片处理完成', icon: 'none' })
      return
    }
    if (!this.data.content.trim()) {
      wx.showToast({ title: '写下一点内容再保存', icon: 'none' })
      return
    }

    this.clearDraftTimer()
    this.saveIdempotencyKey = this.saveIdempotencyKey || createIdempotencyKey()
    this.setData({ saving: true, canSave: false, saveState: 'saving' })

    try {
      const app = getApp()
      const user = app.globalData.userInfo || await auth.ensureLogin({ force: true })
      if (!this.draftUserId && user && user.id) {
        this.draftUserId = user.id
      }
      const successfulImages = this.data.images.filter((image) => image.status === 'success')
      const hasFailedImages = this.data.images.some((image) => image.status === 'failed')
      const response = await api.createDiary({
        content: this.data.content,
        energyScore: this.data.energyScore,
        moodLabel: this.data.moodLabel,
        imageIds: successfulImages.map((image) => image.imageId)
      }, this.saveIdempotencyKey)

      draftService.clearDraft(this.draftUserId)
      this.data.images.forEach(removeLocalImage)
      this.isDirty = false
      this.saveIdempotencyKey = null
      this.setData({
        content: '',
        charCount: 0,
        energyScore: DEFAULT_ENERGY_SCORE,
        moodLabel: getMoodForScore(DEFAULT_ENERGY_SCORE).label,
        images: [],
        uploadingCount: 0,
        saving: false,
        canSave: false,
        saveState: 'success',
        draftStatus: '已保存'
      })
      this.updateUnloadAlert()
      if (hasFailedImages && wx.showModal) {
        wx.showModal({
          title: '文字已保存',
          content: '部分图片上传失败，未添加到日记。',
          showCancel: false,
          confirmText: '知道了'
        })
      } else {
        wx.showToast({ title: '日记已保存', icon: 'success' })
      }
      if (wx.navigateTo && response.data && response.data.diaryId) {
        wx.navigateTo({
          url: `/pages/reflection/reflection?diaryId=${response.data.diaryId}`
        })
      }
    } catch (error) {
      this.isDirty = true
      this.persistDraft()
      this.setData({
        saving: false,
        canSave: canSubmit(this.data.content, this.data.images, false),
        saveState: 'failed'
      })
      wx.showToast({ title: '保存失败，草稿已保留', icon: 'none' })
    }
  }
})
