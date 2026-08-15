const ACCESS_TOKEN_KEY = 'nannan_access_token'
const AUTH_USER_KEY = 'nannan_auth_user'
const LOGGED_OUT_KEY = 'nannan_logged_out'

function getAccessToken() {
  return wx.getStorageSync(ACCESS_TOKEN_KEY) || ''
}

function setAccessToken(token) {
  wx.setStorageSync(ACCESS_TOKEN_KEY, token)
}

function clearAccessToken() {
  wx.removeStorageSync(ACCESS_TOKEN_KEY)
}

function getAuthUser() {
  return wx.getStorageSync(AUTH_USER_KEY) || null
}

function setAuthUser(user) {
  wx.setStorageSync(AUTH_USER_KEY, user)
}

function clearAuthUser() {
  wx.removeStorageSync(AUTH_USER_KEY)
}

function isLoggedOut() {
  return wx.getStorageSync(LOGGED_OUT_KEY) === true
}

function markLoggedOut() {
  wx.setStorageSync(LOGGED_OUT_KEY, true)
}

function clearLoggedOut() {
  wx.removeStorageSync(LOGGED_OUT_KEY)
}

module.exports = {
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  getAuthUser,
  setAuthUser,
  clearAuthUser,
  isLoggedOut,
  markLoggedOut,
  clearLoggedOut
}
