App({
  onLaunch() {
    this.globalData = {
      ...this.globalData,
      launchedAt: Date.now()
    }
  },
  globalData: {
    userInfo: null,
    accessToken: null,
    apiBaseUrl: ''
  }
})
