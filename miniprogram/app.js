const auth = require('./services/auth')

App({
  onLaunch() {
    this.globalData = {
      ...this.globalData,
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
    apiBaseUrl: 'http://127.0.0.1:8000/api/v1'
  }
})
