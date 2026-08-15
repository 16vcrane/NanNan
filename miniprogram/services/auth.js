const api = require('./api')
const storage = require('../utils/storage')

let loginTask = null

function getWechatCode() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(result) {
        if (result.code) {
          resolve(result.code)
          return
        }
        reject(new Error('微信登录未返回有效凭证'))
      },
      fail(error) {
        reject(new Error(error.errMsg || '微信登录失败'))
      }
    })
  })
}

async function loginWithWechat() {
  const app = getApp()
  app.globalData.authStatus = 'loading'

  const code = await getWechatCode()
  const response = await api.login(code)
  storage.setAccessToken(response.data.accessToken)
  app.globalData.accessToken = response.data.accessToken
  app.globalData.userInfo = response.data.user
  app.globalData.authStatus = 'authenticated'
  return response.data.user
}

async function restoreLogin() {
  const app = getApp()
  const token = storage.getAccessToken()
  if (!token) {
    return null
  }

  app.globalData.accessToken = token
  app.globalData.authStatus = 'loading'
  try {
    const response = await api.getCurrentUser()
    app.globalData.userInfo = response.data
    app.globalData.authStatus = 'authenticated'
    return response.data
  } catch (error) {
    if (error.statusCode === 401) {
      storage.clearAccessToken()
      app.globalData.accessToken = null
      app.globalData.userInfo = null
      return null
    }
    app.globalData.authStatus = 'failed'
    throw error
  }
}

function ensureLogin(options = {}) {
  if (loginTask) {
    return loginTask
  }

  loginTask = (async () => {
    if (!options.force) {
      const user = await restoreLogin()
      if (user) {
        return user
      }
    }
    return loginWithWechat()
  })().finally(() => {
    loginTask = null
  })

  return loginTask
}

function clearLogin() {
  const app = getApp()
  storage.clearAccessToken()
  app.globalData.accessToken = null
  app.globalData.userInfo = null
  app.globalData.authStatus = 'idle'
}

module.exports = {
  ensureLogin,
  clearLogin
}
