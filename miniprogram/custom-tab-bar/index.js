Component({
  data: {
    selected: 0,
    color: '#8B7A6B',
    selectedColor: '#6B4933',
    list: [
      {
        pagePath: '/pages/today/today',
        text: '今日',
        iconPath: '/assets/tabbar/home.png',
        selectedIconPath: '/assets/tabbar/home-active.png'
      },
      {
        pagePath: '/pages/timeline/timeline',
        text: '时光',
        iconPath: '/assets/tabbar/time.png',
        selectedIconPath: '/assets/tabbar/time-active.png'
      },
      {
        pagePath: '/pages/profile/profile',
        text: '我的',
        iconPath: '/assets/tabbar/user.png',
        selectedIconPath: '/assets/tabbar/user-active.png'
      }
    ]
  },

  methods: {
    switchTab(event) {
      const index = Number(event.currentTarget.dataset.index)
      const item = this.data.list[index]
      if (!item || index === this.data.selected) return
      this.setData({ selected: index })
      wx.switchTab({ url: item.pagePath })
    }
  }
})
