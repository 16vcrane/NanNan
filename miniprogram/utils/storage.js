const ACCESS_TOKEN_KEY = 'nannan_access_token'
const AUTH_USER_KEY = 'nannan_auth_user'

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

module.exports = {
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  getAuthUser,
  setAuthUser,
  clearAuthUser
}
