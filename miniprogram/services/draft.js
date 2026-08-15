const DRAFT_PREFIX = 'nannan_today_draft_v1_'

function draftKey(userId) {
  return `${DRAFT_PREFIX}${userId}`
}

function getDraft(userId) {
  if (!userId) return null
  return wx.getStorageSync(draftKey(userId)) || null
}

function saveDraft(userId, draft) {
  if (!userId) return
  wx.setStorageSync(draftKey(userId), {
    ...draft,
    updatedAt: Date.now()
  })
}

function clearDraft(userId) {
  if (!userId) return
  wx.removeStorageSync(draftKey(userId))
}

module.exports = {
  getDraft,
  saveDraft,
  clearDraft
}
