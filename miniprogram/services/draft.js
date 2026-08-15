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

function discardDraft(userId) {
  const draft = getDraft(userId)
  if (draft && wx.removeSavedFile) {
    const images = draft.images || []
    images.forEach((image) => {
      if (image.savedFile && image.localPath) {
        wx.removeSavedFile({ filePath: image.localPath })
      }
    })
  }
  clearDraft(userId)
}

module.exports = {
  getDraft,
  saveDraft,
  clearDraft,
  discardDraft
}
