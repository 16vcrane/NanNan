Page({
  data: {},

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar()
    if (tabBar) tabBar.setData({ selected: 2 })
  },

  openAiInfo() {
    wx.navigateTo({
      url: '/pages/ai-info/ai-info'
    })
  }
})
