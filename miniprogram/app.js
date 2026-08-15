const auth = require('./services/auth')
const { getApiBaseUrl } = require('./config/environment')

App({
  onLaunch() {
    this.globalData = {
      ...this.globalData,
      apiBaseUrl: getApiBaseUrl(),
      launchedAt: Date.now()
    }
    this.loginPromise = auth.ensureLogin().catch((error) => {
      this.globalData.authStatus = 'failed'
      console.warn('login initialization failed', error.message)
      return null
    })
  },
  globalData: {
    userInfo: null,
    accessToken: null,
    authStatus: 'idle',
    apiBaseUrl: ''
  }
})
