const DEVELOPMENT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

// Set this to the HTTPS domain registered in the WeChat Mini Program console.
const PRODUCTION_API_BASE_URL = ''

function resolveApiBaseUrl(envVersion) {
  if (!envVersion || envVersion === 'develop') return DEVELOPMENT_API_BASE_URL
  if (!PRODUCTION_API_BASE_URL.startsWith('https://')) {
    throw new Error('正式环境 API 地址尚未配置为 HTTPS 合法域名')
  }
  return PRODUCTION_API_BASE_URL.replace(/\/$/, '')
}

function getApiBaseUrl() {
  const account = wx.getAccountInfoSync ? wx.getAccountInfoSync() : null
  const envVersion = account && account.miniProgram
    ? account.miniProgram.envVersion
    : 'develop'
  return resolveApiBaseUrl(envVersion)
}

module.exports = {
  getApiBaseUrl,
  resolveApiBaseUrl
}
