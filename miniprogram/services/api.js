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

function createDiary(payload) {
  return request({
    url: '/diaries',
    method: 'POST',
    data: payload
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
  createDiary,
  getDiaryList,
  getDiaryDetail,
  deleteDiary,
  getReflection,
  retryReflection,
  deleteUploadedImage
}
