const storage = require('./storage')

function request(options) {
  const app = getApp()
  const token = storage.getAccessToken()
  const header = {
    'content-type': 'application/json',
    ...(options.header || {})
  }

  if (options.auth !== false && token) {
    header.Authorization = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.apiBaseUrl}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header,
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data)
          return
        }

        if (response.statusCode === 401) {
          storage.clearAccessToken()
          app.globalData.accessToken = null
          app.globalData.userInfo = null
          app.globalData.authStatus = 'expired'
        }

        const message = response.data && response.data.message
          ? response.data.message
          : '请求失败，请稍后重试'
        const error = new Error(message)
        error.statusCode = response.statusCode
        error.response = response.data
        reject(error)
      },
      fail(error) {
        reject(new Error(error.errMsg || '网络连接失败'))
      }
    })
  })
}

module.exports = request
