const api = require('../../services/api')
const auth = require('../../services/auth')
const draftService = require('../../services/draft')
const { getMoodForScore } = require('../../config/moods')

const MAX_CONTENT_LENGTH = 3000
const DRAFT_DELAY_MS = 600
const DEFAULT_ENERGY_SCORE = 50

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

Page({
  data: {
    dateText: '',
    greeting: '',
    content: '',
    charCount: 0,
    maxLength: MAX_CONTENT_LENGTH,
    energyScore: DEFAULT_ENERGY_SCORE,
    moodLabel: getMoodForScore(DEFAULT_ENERGY_SCORE).label,
    saving: false,
    canSave: false,
    saveState: 'idle',
    draftStatus: ''
  },

  onLoad() {
    const now = new Date()
    this.draftTimer = null
    this.draftUserId = null
    this.isDirty = false
    this.setData({
      dateText: formatToday(now),
      greeting: greetingForHour(now.getHours())
    })
    this.initializeDraft()
  },

  onHide() {
    this.persistDraft()
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
    this.isDirty = true
    this.setData({
      content,
      charCount: content.length,
      energyScore,
      moodLabel: draft.moodLabel || getMoodForScore(energyScore).label,
      canSave: Boolean(content.trim()),
      draftStatus: '已恢复上次草稿'
    })
    this.updateUnloadAlert()
  },

  handleContentInput(event) {
    const content = event.detail.value
    this.markDirty()
    this.setData({
      content,
      charCount: content.length,
      canSave: Boolean(content.trim()) && !this.data.saving,
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
      moodLabel: this.data.moodLabel
    })
    this.setData({ draftStatus: '已自动保存草稿' })
  },

  async handleSave() {
    if (this.data.saving) return
    if (!this.data.content.trim()) {
      wx.showToast({ title: '写下一点内容再保存', icon: 'none' })
      return
    }

    this.clearDraftTimer()
    this.setData({ saving: true, canSave: false, saveState: 'saving' })

    try {
      const user = await auth.ensureLogin()
      if (!this.draftUserId && user && user.id) {
        this.draftUserId = user.id
      }
      await api.createDiary({
        content: this.data.content,
        energyScore: this.data.energyScore,
        moodLabel: this.data.moodLabel,
        imageIds: []
      })

      draftService.clearDraft(this.draftUserId)
      this.isDirty = false
      this.setData({
        content: '',
        charCount: 0,
        energyScore: DEFAULT_ENERGY_SCORE,
        moodLabel: getMoodForScore(DEFAULT_ENERGY_SCORE).label,
        saving: false,
        canSave: false,
        saveState: 'success',
        draftStatus: '已保存'
      })
      this.updateUnloadAlert()
      wx.showToast({ title: '日记已保存', icon: 'success' })
    } catch (error) {
      this.isDirty = true
      this.persistDraft()
      this.setData({
        saving: false,
        canSave: Boolean(this.data.content.trim()),
        saveState: 'failed'
      })
      wx.showToast({ title: '保存失败，草稿已保留', icon: 'none' })
    }
  }
})
