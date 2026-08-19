const request = require('../utils/request')

function login(code) {
  return request({
    url: '/auth/login',
    method: 'POST',
    data: { code },
    auth: false
  })
}

function getCurrentUser() {
  return request({ url: '/users/me' })
}

function deleteCurrentUser() {
  return request({
    url: '/users/me',
    method: 'DELETE'
  })
}

function createDiary(payload, idempotencyKey) {
  return request({
    url: '/diaries',
    method: 'POST',
    data: payload,
    header: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : undefined
  })
}

function getDiaryList(params = {}) {
  const page = params.page || 1
  const limit = params.limit || 20
  return request({ url: `/diaries?page=${page}&limit=${limit}` })
}

function getDiaryDetail(diaryId) {
  return request({ url: `/diaries/${diaryId}` })
}

function getOnThisDay(timezone) {
  const tz = timezone ? `?timezone=${encodeURIComponent(timezone)}` : ''
  return request({ url: `/memories/on-this-day${tz}` })
}

function deleteDiary(diaryId) {
  return request({
    url: `/diaries/${diaryId}`,
    method: 'DELETE'
  })
}

function getReflection(diaryId) {
  return request({ url: `/diaries/${diaryId}/reflection` })
}

function retryReflection(diaryId) {
  return request({
    url: `/diaries/${diaryId}/reflection/retry`,
    method: 'POST'
  })
}

function deleteUploadedImage(imageId) {
  return request({
    url: `/uploads/images/${imageId}`,
    method: 'DELETE'
  })
}

module.exports = {
  login,
  getCurrentUser,
  deleteCurrentUser,
  createDiary,
  getDiaryList,
  getDiaryDetail,
  getOnThisDay,
  deleteDiary,
  getReflection,
  retryReflection,
  deleteUploadedImage
}
