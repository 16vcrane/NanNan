Component({
  properties: {
    images: {
      type: Array,
      value: []
    },
    maxCount: {
      type: Number,
      value: 3
    },
    disabled: {
      type: Boolean,
      value: false
    }
  },

  methods: {
    chooseImages() {
      if (this.properties.disabled) return
      const remaining = this.properties.maxCount - this.properties.images.length
      if (remaining <= 0) return
      wx.chooseMedia({
        count: remaining,
        mediaType: ['image'],
        sourceType: ['album', 'camera'],
        sizeType: ['compressed'],
        success: (result) => {
          this.triggerEvent('select', { files: result.tempFiles })
        }
      })
    },

    removeImage(event) {
      this.triggerEvent('remove', {
        localId: event.currentTarget.dataset.id
      })
    },

    retryImage(event) {
      this.triggerEvent('retry', {
        localId: event.currentTarget.dataset.id
      })
    },

    previewImage(event) {
      const localId = event.currentTarget.dataset.id
      const current = this.properties.images.find((image) => image.localId === localId)
      const urls = this.properties.images
        .map((image) => image.localPath)
        .filter(Boolean)
      if (!current || !current.localPath || !urls.length) return
      wx.previewImage({ current: current.localPath, urls })
    }
  }
})
