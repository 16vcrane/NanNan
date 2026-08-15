const api = require('./api')
const storage = require('../utils/storage')

const CLEANUP_PREFIX = 'nannan_image_cleanup_v1_'

function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function expireAuth(app) {
  storage.clearAccessToken()
  storage.clearAuthUser()
  app.globalData.accessToken = null
  app.globalData.userInfo = null
  app.globalData.authStatus = 'expired'
}

function uploadImage(filePath) {
  const app = getApp()
  const token = storage.getAccessToken()
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${app.globalData.apiBaseUrl}/uploads/images`,
      filePath,
      name: 'file',
      header: authHeader(token),
      success(response) {
        let payload
        try {
          payload = JSON.parse(response.data)
        } catch (error) {
          reject(new Error('图片上传响应异常'))
          return
        }
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(payload.data)
          return
        }
        if (response.statusCode === 401) {
          expireAuth(app)
        }
        reject(new Error(payload.message || '图片上传失败'))
      },
      fail(error) {
        reject(new Error(error.errMsg || '图片上传失败'))
      }
    })
  })
}

function deleteImage(imageId) {
  return api.deleteUploadedImage(imageId)
}

function downloadImage(image) {
  const app = getApp()
  const token = storage.getAccessToken()
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url: `${app.globalData.apiBaseUrl.replace(/\/api\/v1$/, '')}${image.url}`,
      header: authHeader(token),
      success(response) {
        if (response.statusCode === 200) {
          resolve(response.tempFilePath)
          return
        }
        if (response.statusCode === 401) {
          expireAuth(app)
        }
        reject(new Error('图片下载失败'))
      },
      fail(error) {
        reject(new Error(error.errMsg || '图片下载失败'))
      }
    })
  })
}

function cleanupKey(userId) {
  return `${CLEANUP_PREFIX}${userId}`
}

function clearCleanup(userId) {
  if (userId) wx.removeStorageSync(cleanupKey(userId))
}

function enqueueCleanup(userId, imageId) {
  if (!userId || !imageId) return
  const key = cleanupKey(userId)
  const queue = wx.getStorageSync(key) || []
  if (!queue.includes(imageId)) {
    wx.setStorageSync(key, [...queue, imageId])
  }
}

async function flushCleanup(userId) {
  if (!userId) return
  const key = cleanupKey(userId)
  const queue = wx.getStorageSync(key) || []
  const remaining = []
  for (const imageId of queue) {
    try {
      await deleteImage(imageId)
    } catch (error) {
      remaining.push(imageId)
    }
  }
  if (remaining.length) {
    wx.setStorageSync(key, remaining)
  } else {
    wx.removeStorageSync(key)
  }
}

module.exports = {
  uploadImage,
  deleteImage,
  downloadImage,
  enqueueCleanup,
  flushCleanup,
  clearCleanup
}
