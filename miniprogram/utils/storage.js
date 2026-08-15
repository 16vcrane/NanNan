const ACCESS_TOKEN_KEY = 'nannan_access_token'

function getAccessToken() {
  return wx.getStorageSync(ACCESS_TOKEN_KEY) || ''
}

function setAccessToken(token) {
  wx.setStorageSync(ACCESS_TOKEN_KEY, token)
}

function clearAccessToken() {
  wx.removeStorageSync(ACCESS_TOKEN_KEY)
}

module.exports = {
  getAccessToken,
  setAccessToken,
  clearAccessToken
}
